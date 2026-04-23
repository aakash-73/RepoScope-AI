import asyncio
from datetime import datetime
from database import get_db
from services.groq_service import call_groq

STRUCTURED_PROMPT = """
You are an expert software architect analysing a single file in a codebase.

File path: {file_path}
File content:
{file_content}

This file directly imports the following files. Here are their one-line summaries:
{dependency_summaries}

This file is imported by the following files:
{dependents_list}

Graph metrics:
- Complexity score: {complexity_score}/10
- Dependency depth: {depth_score}
- Incoming connections: {incoming_count}
- Outgoing connections: {outgoing_count}

Respond ONLY with a valid JSON object in this exact structure, no extra text:
{{
  "purpose": "what this file does in one paragraph",
  "exports": ["list of what this file exposes to other files"],
  "why_connected_to": {{
    "filename": "reason this specific import exists"
  }},
  "architectural_role": "one of: entry_point / controller / service / model / helper / config / style / test",
  "functional_categories": ["list of high-level functional systems this node belongs to (e.g. 'Authentication', 'AI Services', 'Database Integration'). Look at dependents_list to map ubiquitous files like configs to multiple overlapping categories based on what systems call them!"],
  "key_patterns": ["patterns and frameworks detected"],
  "concerns": ["potential architectural issues if any"],
  "summary_for_dependents": "one line summary for files that import this"
}}
"""

async def analyze_all_nodes(repo_id: str):
    """
    Main entry point. Called after repo ingestion completes.
    Processes all nodes one at a time in dependency order (leaves first).
    Sequential processing ensures:
      - accurate solidification animation (one node lights up at a time)
      - lower hardware load (no concurrent LLM calls)
      - dependency summaries are always available when a file is analyzed
    """
    db = get_db()

    # Mark repo analysis as pending
    await db.repo_analysis.update_one(
        {"repo_id": repo_id},
        {"$set": {"status": "pending", "analyzed_at": datetime.utcnow()}},
        upsert=True
    )

    # Fetch all file nodes for this repo
    cursor = db.files.find({"repo_id": repo_id})
    files = await cursor.to_list(length=None)

    # Sort nodes: leaves first so dependencies are analyzed before importers
    sorted_files = _sort_by_dependency_order(files)

    # Mark repository as analyzing
    await db.repositories.update_one(
        {"repo_id": repo_id},
        {"$set": {"analysis_status": "analyzing"}}
    )

    # Mark only non-completed nodes as pending in both collections
    for file in sorted_files:
        path = file["path"]
        existing = await db.node_analysis.find_one(
            {"repo_id": repo_id, "file_path": path}, {"status": 1}
        )
        if not existing or existing.get("status") != "done":
            await db.node_analysis.update_one(
                {"repo_id": repo_id, "file_path": path},
                {"$set": {"status": "pending"}},
                upsert=True
            )
            # Sync to files collection for graph ghosting
            await db.files.update_one(
                {"repo_id": repo_id, "path": path},
                {"$set": {"analysis_status": "pending"}}
            )

    # ── Parallel leaves + sequential dependents ───────────────────────────────
    # Files with NO imports are true leaves and have no dependencies to wait for.
    # We analyze them in concurrent batches (max 3 at once) to save time.
    # Files that import others must still run sequentially in topological order
    # so that _fetch_dependency_summaries always finds a ready "done" summary.

    leaf_files = [f for f in sorted_files if not f.get("imports")]
    dep_files  = [f for f in sorted_files if f.get("imports")]

    async def _analyze_if_needed(file):
        existing = await db.node_analysis.find_one(
            {"repo_id": repo_id, "file_path": file["path"]}, {"status": 1}
        )
        if existing and existing.get("status") == "done":
            await db.files.update_one(
                {"repo_id": repo_id, "path": file["path"]},
                {"$set": {"analysis_status": "done"}}
            )
            return
        await _analyze_single_node(repo_id, file, files)

    BATCH_SIZE = 3
    for i in range(0, len(leaf_files), BATCH_SIZE):
        batch = leaf_files[i:i + BATCH_SIZE]
        await asyncio.gather(*[_analyze_if_needed(f) for f in batch])

    for file in dep_files:
        await _analyze_if_needed(file)

    await analyze_repo_level(repo_id)



async def _analyze_single_node(repo_id: str, file: dict, all_files: list):
    """
    Analyses one file node and saves the result to MongoDB.
    Called sequentially — never concurrently.
    """
    db = get_db()
    file_path = file["path"]

    # Mark as analyzing in both collections
    await db.node_analysis.update_one(
        {"repo_id": repo_id, "file_path": file_path},
        {"$set": {"status": "analyzing"}}
    )
    await db.files.update_one(
        {"repo_id": repo_id, "path": file_path},
        {"$set": {"analysis_status": "analyzing"}}
    )

    try:
        # Gather dependency summaries — because we process in topological order,
        # all dependencies of this file are already "done" at this point.
        outgoing = file.get("imports", [])
        dependency_summaries = await _fetch_dependency_summaries(repo_id, outgoing)

        # Gather dependents list (who imports this file)
        incoming = [f["path"] for f in all_files if file_path in f.get("imports", [])]

        # Build prompt
        prompt = STRUCTURED_PROMPT.format(
            file_path=file_path,
            file_content=file.get("content", "")[:6000],
            dependency_summaries=dependency_summaries,
            dependents_list=", ".join(incoming) if incoming else "None",
            complexity_score=file.get("complexity_score", "N/A"),
            depth_score=file.get("depth_score", "N/A"),
            incoming_count=len(incoming),
            outgoing_count=len(outgoing)
        )

        # Call LLM (Ollama via groq_service alias)
        response = await call_groq(prompt)
        analysis = _parse_json_response(response)

        # Save successful result
        await db.node_analysis.update_one(
            {"repo_id": repo_id, "file_path": file_path},
            {"$set": {
                "analysis": analysis,
                "status": "done",
                "analyzed_at": datetime.utcnow()
            }}
        )
        await db.files.update_one(
            {"repo_id": repo_id, "path": file_path},
            {"$set": {"analysis_status": "done"}}
        )

        # ── NEW: Populate Knowledge Graph triplets ────────────────────────────
        await _update_knowledge_graph(repo_id, file_path, analysis)

    except Exception as e:
        # Write failure to both collections so the node doesn't stay stuck
        # on "analyzing" in the UI forever
        await db.node_analysis.update_one(
            {"repo_id": repo_id, "file_path": file_path},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        await db.files.update_one(
            {"repo_id": repo_id, "path": file_path},
            {"$set": {"analysis_status": "failed"}}
        )


async def _update_knowledge_graph(repo_id: str, file_path: str, analysis: dict):
    """
    Decomposes file analysis into a semantic graph of nodes and edges.
    Stores File -> BELONGS_TO -> Category, File -> HAS_ROLE -> Role, etc.
    """
    db = get_db()
    file_id = file_path # Unique ID for file nodes is their path

    # 1. Upsert File Node
    await db.kg_nodes.update_one(
        {"repo_id": repo_id, "id": file_id},
        {"$set": {
            "type": "file",
            "label": file_path.split("/")[-1],
            "properties": {
                "purpose": analysis.get("purpose", ""),
                "summary": analysis.get("summary_for_dependents", ""),
                "status": "analyzed"
            }
        }},
        upsert=True
    )

    # 2. Extract and Upsert Categories
    categories = analysis.get("functional_categories", [])
    for cat_name in categories:
        cat_id = f"cat__{cat_name.lower().replace(' ', '_')}"
        await db.kg_nodes.update_one(
            {"repo_id": repo_id, "id": cat_id},
            {"$set": {
                "type": "category",
                "label": cat_name,
                "properties": {"source": "llm_analysis"}
            }},
            upsert=True
        )
        # Create Edge
        await db.kg_edges.update_one(
            {"repo_id": repo_id, "source": file_id, "target": cat_id, "relation": "belongs_to"},
            {"$set": {"weight": 1.0}},
            upsert=True
        )

    # 3. Extract and Upsert Architectural Role
    role_name = analysis.get("architectural_role", "unknown")
    if role_name != "unknown":
        role_id = f"role__{role_name.lower()}"
        await db.kg_nodes.update_one(
            {"repo_id": repo_id, "id": role_id},
            {"$set": {
                "type": "role",
                "label": role_name.replace("_", " ").title(),
                "properties": {"source": "llm_analysis"}
            }},
            upsert=True
        )
        # Create Edge
        await db.kg_edges.update_one(
            {"repo_id": repo_id, "source": file_id, "target": role_id, "relation": "has_role"},
            {"$set": {"weight": 1.0}},
            upsert=True
        )

    # 4. Extract and Upsert Key Patterns
    patterns = analysis.get("key_patterns", [])
    for pat_name in patterns:
        pat_id = f"pat__{pat_name.lower().replace(' ', '_')}"
        await db.kg_nodes.update_one(
            {"repo_id": repo_id, "id": pat_id},
            {"$set": {
                "type": "pattern",
                "label": pat_name,
                "properties": {"source": "llm_analysis"}
            }},
            upsert=True
        )
        # Create Edge
        await db.kg_edges.update_one(
            {"repo_id": repo_id, "source": file_id, "target": pat_id, "relation": "implements"},
            {"$set": {"weight": 1.0}},
            upsert=True
        )

    # 5. Connect structural imports (already present in 'files' but mirroring here for KG completeness)
    # This is handled during ingestion in build_dependency_graph, but we can sync it here
    # to ensure the KG is a complete source of truth for both structural and semantic edges.
    file_doc = await db.files.find_one({"repo_id": repo_id, "path": file_path}, {"imports": 1})
    if file_doc and "imports" in file_doc:
        for imp_path in file_doc["imports"]:
            await db.kg_edges.update_one(
                {"repo_id": repo_id, "source": file_id, "target": imp_path, "relation": "imports"},
                {"$set": {"weight": 1.0}},
                upsert=True
            )


async def _fetch_dependency_summaries(repo_id: str, file_paths: list) -> str:
    """
    Fetches the one-line summary of already-analyzed dependencies.
    Since we process in topological order, these will almost always be "done".
    Falls back to file path string if not yet analyzed (handles cycles).
    """
    db = get_db()
    summaries = []
    for path in file_paths:
        doc = await db.node_analysis.find_one(
            {"repo_id": repo_id, "file_path": path, "status": "done"},
            {"analysis.summary_for_dependents": 1}
        )
        if doc:
            summaries.append(f"{path}: {doc['analysis']['summary_for_dependents']}")
        else:
            summaries.append(f"{path}: (not yet analyzed)")
    return "\n".join(summaries) if summaries else "None"


def _sort_by_dependency_order(files: list) -> list:
    """
    Topological sort using Kahn's algorithm.
    Files with no outgoing edges (leaves) come first so that when a file is
    analyzed, all files it imports have already been processed.
    """
    from collections import defaultdict, deque

    file_paths = [f["path"] for f in files]
    file_map = {f["path"]: f for f in files}

    outgoing_count = defaultdict(int)
    dependents = defaultdict(list)

    for file in files:
        src = file["path"]
        imports = file.get("imports", [])
        for tgt in imports:
            if tgt in file_map:
                outgoing_count[src] += 1
                dependents[tgt].append(src)

    queue = deque([p for p in file_paths if outgoing_count[p] == 0])
    sorted_paths = []

    while queue:
        path = queue.popleft()
        sorted_paths.append(path)
        for dep in dependents[path]:
            outgoing_count[dep] -= 1
            if outgoing_count[dep] == 0:
                queue.append(dep)

    # Append any remaining (handles circular dependencies)
    remaining = [p for p in file_paths if p not in sorted_paths]
    sorted_paths.extend(remaining)

    return [file_map[p] for p in sorted_paths if p in file_map]


def _parse_json_response(response: str) -> dict:
    import json
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception:
        return {
            "purpose": response,
            "exports": [],
            "why_connected_to": {},
            "architectural_role": "unknown",
            "key_patterns": [],
            "concerns": [],
            "summary_for_dependents": response[:200]
        }


REPO_SYNTHESIS_PROMPT = """
You are an expert software architect. You have been given the analysed summaries of every file in a codebase, grouped by architectural layer.

Repository ID: {repo_id}

Frontend layer files:
{frontend_summaries}

Backend layer files:
{backend_summaries}

Database layer files:
{database_summaries}

DevOps layer files:
{devops_summaries}

Entry points detected: {entry_points}

Respond ONLY with a valid JSON object in this exact structure, no extra text:
{{
  "overall_summary": "2-3 paragraph plain English description of what this repository does and how it is structured",
  "data_flow": "plain English description of how data moves through the system from entry to storage",
  "architectural_patterns": ["list of patterns detected e.g. MVC, REST, microservices"],
  "layer_summaries": {{
    "frontend": "one paragraph summary of the frontend layer",
    "backend": "one paragraph summary of the backend layer",
    "database": "one paragraph summary of the database layer",
    "devops": "one paragraph summary of the devops layer"
  }}
}}
"""

async def analyze_repo_level(repo_id: str):
    """
    Runs after all nodes are analyzed.
    Synthesizes node summaries into a repo-wide understanding.
    """
    db = get_db()
    await db.repo_analysis.update_one(
        {"repo_id": repo_id},
        {"$set": {"status": "analyzing"}}
    )

    try:
        # Fetch all completed node analyses
        cursor = db.node_analysis.find(
            {"repo_id": repo_id, "status": "done"}
        )
        nodes = await cursor.to_list(length=None)

        # Group by architectural layer using analysis results
        layers = {"frontend": [], "backend": [], "database": [], "devops": [], "other": []}
        entry_points = []

        for node in nodes:
            role = node["analysis"].get("architectural_role", "other")
            summary = f"{node['file_path']}: {node['analysis'].get('summary_for_dependents', '')}"

            if role in ["entry_point", "controller", "service"]:
                layers["backend"].append(summary)
            elif role in ["style", "component"]:
                layers["frontend"].append(summary)
            elif role in ["model"]:
                layers["database"].append(summary)
            elif role in ["config"]:
                layers["devops"].append(summary)
            else:
                layers["other"].append(summary)

            if role == "entry_point":
                entry_points.append(node["file_path"])

        # Build prompt
        prompt = REPO_SYNTHESIS_PROMPT.format(
            repo_id=repo_id,
            frontend_summaries="\n".join(layers["frontend"][:30]) or "None",
            backend_summaries="\n".join(layers["backend"][:30]) or "None",
            database_summaries="\n".join(layers["database"][:20]) or "None",
            devops_summaries="\n".join(layers["devops"][:10]) or "None",
            entry_points=", ".join(entry_points) if entry_points else "Not detected"
        )

        # Call LLM
        response = await call_groq(prompt)
        analysis = _parse_json_response(response)

        # Save result
        await db.repo_analysis.update_one(
            {"repo_id": repo_id},
            {"$set": {
                **analysis,
                "entry_points": entry_points,
                "status": "done",
                "analyzed_at": datetime.utcnow()
            }}
        )

        # Update repo to final understood state
        await db.repositories.update_one(
            {"repo_id": repo_id},
            {"$set": {"analysis_status": "understood"}}
        )

    except Exception as e:
        await db.repo_analysis.update_one(
            {"repo_id": repo_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )