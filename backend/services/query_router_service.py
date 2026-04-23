import json
import logging
import re
from typing import Optional, Dict, Any, List
import openai
from openai import AsyncOpenAI
from config import settings
from database import get_db

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are a query intent router for a codebase search engine.
Classify the user's query into one of these strategies:
1. `exact_match`: They are asking for a specific function, class, framework, or API route (e.g. "Where is the login function?", "Find all FastAPI routes").
2. `fuzzy_search`: They are asking for a general concept or keyword (e.g. "auth mechanism", "database connection").
3. `semantic`: They want to find files by architectural role or pattern (e.g. "show me all controllers", "what are the database models?").
4. `graph`: They are asking about impact or dependencies (e.g. "what breaks if I change X?", "what imports Y?").
5. `hive_search`: They are asking about a high-level system, concept, or functional domain (e.g. "which local llm is used?", "how does auth work?").
6. `unknown`: The query is non-technical, conversational, or too complex to classify.

If you choose `hive_search`, you MUST pick the most relevant conceptual themes from this available list of categories discovered in the repo:
{available_categories}

Respond ONLY with a valid JSON object in this exact structure:
{{
  "strategy": "exact_match | fuzzy_search | semantic | graph | hive_search | unknown",
  "entities": ["list of strings representing extracted keywords, function names, frameworks, roles, filenames, or EXACT target categories from the available list if hive_search"]
}}
"""

_router_client = AsyncOpenAI(
    base_url=settings.OLLAMA_BASE_URL,
    api_key="ollama",
)

def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_core_keywords(entities: List[str]) -> List[str]:
    """
    Break multi-word entity phrases into individual core keywords.
    e.g. ["service files", "controllers"] -> ["service", "files", "controller", "controllers"]
    Also deduplicates and strips common stop words.
    """
    STOP_WORDS = {"files", "the", "a", "an", "all", "of", "for", "and", "or", "with", "in", "on", "to"}
    keywords = set()
    for entity in entities:
        # Split on spaces and hyphens
        parts = re.split(r"[\s\-_]+", entity.lower())
        for part in parts:
            part = part.strip()
            if part and part not in STOP_WORDS and len(part) > 1:
                keywords.add(part)
                # Also add singular form for simple plurals
                if part.endswith("s") and len(part) > 3:
                    keywords.add(part[:-1])
    # Always include the original entities too (for exact matches)
    for entity in entities:
        if entity.strip():
            keywords.add(entity.strip())
    return list(keywords)


def _score_files_by_relevance(files: List[dict], query: str) -> List[dict]:
    """
    Re-rank retrieved files by keyword overlap with the query.
    Returns top 15 most relevant files.
    """
    query_words = set(re.findall(r"\w+", query.lower()))
    STOP = {"the", "a", "an", "is", "are", "what", "how", "where", "does", "do", "it", "this", "i", "me", "my"}
    query_words -= STOP

    def score(f: dict) -> int:
        text = " ".join([
            f.get("path", ""),
            f.get("name", ""),
            " ".join(f.get("imports", [])),
            " ".join(f.get("exports", [])),
            f.get("content", "")[:500],
        ]).lower()
        return sum(1 for w in query_words if w in text)

    scored = sorted(files, key=score, reverse=True)
    return scored[:15]


async def determine_intent(repo_id: str, query: str) -> dict:
    try:
        db = get_db()
        categories = await db.node_analysis.distinct("analysis.functional_categories", {"repo_id": repo_id})
        cats_str = ", ".join(categories) if categories else "None detected yet"
        prompt = ROUTER_SYSTEM_PROMPT.format(available_categories=cats_str)

        response = await _router_client.chat.completions.create(
            model=settings.OLLAMA_CHAT_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.0
        )
        content = _strip_thinking(response.choices[0].message.content or "{}")
        
        clean = content.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        return json.loads(clean.strip())
    except Exception as e:
        logger.warning(f"Router intent classification failed: {e}")
        return {"strategy": "unknown", "entities": []}


async def query_exact_match(repo_id: str, entities: List[str]) -> List[dict]:
    db = get_db()
    if not entities:
        return []

    # Use $elemMatch per entity for array fields, direct regex for string fields
    or_clauses = []
    for e in entities:
        pattern = {"$regex": f"^{re.escape(e)}$", "$options": "i"}
        or_clauses.append({"exports": {"$elemMatch": pattern}})
        or_clauses.append({"imports": {"$elemMatch": pattern}})
        or_clauses.append({"name": pattern})
        or_clauses.append({"path": {"$regex": re.escape(e), "$options": "i"}})

    cursor = db.files.find({
        "repo_id": repo_id,
        "$or": or_clauses
    })
    return await cursor.to_list(length=30)


async def query_fuzzy_search(repo_id: str, entities: List[str]) -> List[dict]:
    db = get_db()
    query_str = " ".join(entities)
    if not query_str:
        return []
    cursor = db.files.find({
        "repo_id": repo_id,
        "$text": {"$search": query_str}
    }).sort([("score", {"$meta": "textScore"})])
    return await cursor.to_list(length=20)


async def query_semantic(repo_id: str, entities: List[str]) -> List[dict]:
    db = get_db()
    if not entities:
        return []

    # Extract core keywords from potentially multi-word phrases
    keywords = _extract_core_keywords(entities)
    logger.info(f"Semantic search keywords: {keywords}")

    # Build $or clauses — $elemMatch for array fields, direct $regex for string fields
    or_clauses = []
    for kw in keywords:
        pattern = {"$regex": kw, "$options": "i"}
        or_clauses.append({"analysis.architectural_role": pattern})
        or_clauses.append({"analysis.key_patterns": {"$elemMatch": pattern}})
        or_clauses.append({"analysis.functional_categories": {"$elemMatch": pattern}})

    cursor = db.node_analysis.find({
        "repo_id": repo_id,
        "$or": or_clauses
    })
    results = await cursor.to_list(length=30)

    file_paths = [r["file_path"] for r in results]
    if not file_paths:
        return []

    f_cursor = db.files.find({"repo_id": repo_id, "path": {"$in": file_paths}})
    return await f_cursor.to_list(length=30)


async def query_graph(repo_id: str, entities: List[str]) -> List[dict]:
    db = get_db()
    if not entities:
        return []

    # Extract core keywords and build partial regex matching on path or name
    keywords = _extract_core_keywords(entities)
    path_or = []
    for kw in keywords:
        pat = {"$regex": kw, "$options": "i"}
        path_or.append({"path": pat})
        path_or.append({"name": pat})

    pipeline = [
        {"$match": {"repo_id": repo_id, "$or": path_or}},
        {
            "$graphLookup": {
                "from": "files",
                "startWith": "$path",
                "connectFromField": "path",
                "connectToField": "imports",
                "as": "dependents",
                "maxDepth": 2,
                "restrictSearchWithMatch": {"repo_id": repo_id}
            }
        }
    ]
    cursor = db.files.aggregate(pipeline)
    results = await cursor.to_list(length=20)

    final_files = []
    seen = set()
    for root in results:
        if root["path"] not in seen:
            seen.add(root["path"])
            final_files.append(root)
        for dep in root.get("dependents", []):
            if dep["path"] not in seen:
                seen.add(dep["path"])
                final_files.append(dep)

    return final_files


async def query_hive_search(repo_id: str, entities: List[str]) -> List[dict]:
    db = get_db()
    if not entities:
        return []

    # Fuzzy match category labels using $regex instead of exact $in
    cat_or = [{"label": {"$regex": e, "$options": "i"}} for e in entities]
    cat_cursor = db.kg_nodes.find({
        "repo_id": repo_id,
        "type": "category",
        "$or": cat_or,
    }, {"id": 1})
    categories = await cat_cursor.to_list(length=None)
    cat_ids = [c["id"] for c in categories]

    if not cat_ids:
        # Fallback: search node_analysis functional_categories with regex
        kws = _extract_core_keywords(entities)
        kw_or = [{"analysis.functional_categories": {"$elemMatch": {"$regex": kw, "$options": "i"}}} for kw in kws]
        cursor = db.node_analysis.find({
            "repo_id": repo_id,
            "$or": kw_or
        })
        results = await cursor.to_list(length=20)
        file_paths = [r["file_path"] for r in results]
    else:
        edge_cursor = db.kg_edges.find({
            "repo_id": repo_id,
            "target": {"$in": cat_ids},
            "relation": "belongs_to"
        }, {"source": 1})
        edges = await edge_cursor.to_list(length=None)
        file_paths = list(set(e["source"] for e in edges))

    if not file_paths:
        return []

    f_cursor = db.files.find({"repo_id": repo_id, "path": {"$in": file_paths}})
    return await f_cursor.to_list(length=15)


async def execute_router_search(repo_id: str, query: str) -> tuple[Optional[str], str]:
    """
    Returns: (strategy, formatted_context_str)
    If strategy is None, we fallback to passing the full repository context.
    """
    intent = await determine_intent(repo_id, query)
    strategy = intent.get("strategy", "unknown")
    entities = intent.get("entities", [])

    logger.info(f"Router classified query as '{strategy}' with entities: {entities}")

    files = []
    if strategy == "exact_match":
        files = await query_exact_match(repo_id, entities)
    elif strategy == "fuzzy_search":
        files = await query_fuzzy_search(repo_id, entities)
    elif strategy == "semantic":
        files = await query_semantic(repo_id, entities)
    elif strategy == "graph":
        files = await query_graph(repo_id, entities)
    elif strategy == "hive_search":
        files = await query_hive_search(repo_id, entities)

    if not files:
        logger.info(f"Router strategy '{strategy}' yielded no results. Falling back to full repo context.")
        return None, ""

    # Re-rank by keyword relevance and cap to top 15
    files = _score_files_by_relevance(files, query)
    logger.info(f"Router strategy '{strategy}' yielded {len(files)} files after re-ranking.")

    # Build context
    from services.repo_chat_service import build_repo_context
    db = get_db()

    paths = [f["path"] for f in files]
    expl_cursor = db.node_analysis.find({"repo_id": repo_id, "file_path": {"$in": paths}, "status": "done"})
    explanations_docs = await expl_cursor.to_list(length=None)
    explanations_map = {doc["file_path"]: json.dumps(doc.get("analysis", {}), indent=2) for doc in explanations_docs}

    context_str = build_repo_context(files, explanations_map)
    info_str = f"Filtered context resolved via '{strategy}' index lookup for {len(files)} files.\n\n{context_str}"

    return strategy, info_str
