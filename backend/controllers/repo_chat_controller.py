from database import get_db
from services.repo_chat_service import summarize_repo, chat_with_repo, build_communication_map, get_pre_analyzed_repo_context
from services.graph_builder import build_dependency_graph
import logging

logger = logging.getLogger(__name__)

async def get_chat_history(repo_id: str) -> list:
    db = get_db()
    doc = await db.repo_chat_history.find_one({"repo_id": repo_id})
    return doc.get("messages", []) if doc else []


async def save_chat_history(repo_id: str, messages: list) -> None:
    db = get_db()
    await db.repo_chat_history.update_one(
        {"repo_id": repo_id},
        {"$set": {"repo_id": repo_id, "messages": messages[-60:]}},
        upsert=True,
    )


async def clear_chat_history(repo_id: str) -> None:
    db = get_db()
    await db.repo_chat_history.delete_one({"repo_id": repo_id})

async def get_proactive_insights(repo_id: str) -> dict:
    db = get_db()

    cached = await db.repo_understandings.find_one({"repo_id": repo_id})
    if cached and cached.get("insights"):
        return {"insights": cached["insights"]}

    understanding = cached.get("understanding") if cached else None
    if not understanding:
        return {"insights": []}

    from services.repo_chat_service import get_chat_client, CHAT_MODEL

    prompt = (
        "Based on the repository understanding below, generate 3-5 concise proactive insights "
        "a developer would find immediately useful. Focus on: architectural concerns, "
        "potential issues, coupling hotspots, or notable patterns. "
        "Respond ONLY with a JSON array, no markdown, no explanation. "
        'Each item: {"type": "warning"|"info"|"tip", "title": "short title", "body": "1-2 sentence insight"}\n\n'
        f"REPOSITORY UNDERSTANDING:\n{understanding[:6000]}"
    )

    try:
        client = get_chat_client()
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3,
        )
        import json
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        insights = json.loads(text.strip())

        await db.repo_understandings.update_one(
            {"repo_id": repo_id},
            {"$set": {"insights": insights}},
        )
        return {"insights": insights}

    except Exception as e:
        logger.warning("Failed to generate proactive insights for repo %s", repo_id, exc_info=True)
        return {"insights": []}

async def get_repo_summary(repo_id: str) -> dict:
    db = get_db()

    repo = await db.repositories.find_one({"repo_id": repo_id})
    if not repo:
        raise ValueError(f"Repository {repo_id} not found")

    cached = await db.repo_understandings.find_one(
        {"repo_id": repo_id}, {"_id": 0}
    )

    if cached and cached.get("summary"):
        logger.info("Full cache hit (summary) for repo %s", repo_id)
        return {
            "repo_id":    repo_id,
            "repo_name":  repo.get("name", repo_id),
            "file_count": repo.get("file_count", 0),
            "summary":    cached["summary"],
        }

    if cached and cached.get("understanding"):
        logger.info("Partial cache hit (understanding only) for repo %s", repo_id)
        from services.repo_chat_service import get_chat_client, CHAT_MODEL, CHAT_SYSTEM_PROMPT

        chat_client = get_chat_client()
        response = await chat_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        CHAT_SYSTEM_PROMPT
                        + "\n\n---\nREPOSITORY UNDERSTANDING DOCUMENT:\n"
                        + cached["understanding"]
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Please give me a concise, friendly overview of this project "
                        "in 150-200 words — what it does, the tech stack, and the overall architecture."
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=600,
        )
        summary = response.choices[0].message.content or "Could not generate summary."

        await db.repo_understandings.update_one(
            {"repo_id": repo_id},
            {"$set": {"summary": summary}},
        )
        return {
            "repo_id":    repo_id,
            "repo_name":  repo.get("name", repo_id),
            "file_count": repo.get("file_count", 0),
            "summary":    summary,
        }

    logger.info("Cache miss — running full analysis for repo %s", repo_id)

    cursor = db.files.find(
        {"repo_id": repo_id},
        {"_id": 0, "path": 1, "name": 1, "extension": 1, "size": 1, "language": 1, "content": 1, "imports": 1, "exports": 1, "github_url": 1},
    )
    files = await cursor.to_list(length=None)

    if not files:
        raise ValueError(f"No files found for repository {repo_id}")

    # Orchestrate enhanced context
    logger.info("Building dependency graph and fetching file explanations for %s", repo_id)
    graph_data = await build_dependency_graph(files, repo_id=repo_id)
    comm_map = build_communication_map(graph_data["nodes"], graph_data["edges"])
    
    # Fetch all available file explanations
    expl_cursor = db.file_explanations.find({"repo_id": repo_id})
    expl_docs = await expl_cursor.to_list(length=None)
    file_explanations = {d["path"]: d["explanation"] for d in expl_docs}

    understanding, summary = await summarize_repo(files, file_explanations, comm_map)

    await db.repo_understandings.update_one(
        {"repo_id": repo_id},
        {"$set": {
            "repo_id":      repo_id,
            "understanding": understanding,
            "summary":       summary,
        }},
        upsert=True,
    )
    logger.info("Stored understanding + summary for repo %s", repo_id)

    return {
        "repo_id":    repo_id,
        "repo_name":  repo.get("name", repo_id),
        "file_count": repo.get("file_count", 0),
        "summary":    summary,
    }

async def repo_chat(repo_id: str, query: str, history: list[dict]) -> dict:
    """
    Answer a user question using the cached understanding document.
    Never touches raw file content — always uses the pre-built understanding.
    """
    db = get_db()

    # 1. First run the deterministic query router
    from services.query_router_service import execute_router_search
    strategy, filtered_context = await execute_router_search(repo_id, query)
    
    if strategy:
        logger.info("Using filtered router context (strategy: %s) for chat: %s", strategy, repo_id)
        reply = await chat_with_repo(filtered_context, query, history)
        return {"reply": reply}

    # 2. Fallback to pre-analyzed context
    pre_analyzed = await get_pre_analyzed_repo_context(repo_id)
    if pre_analyzed:
        logger.info("Using pre-analyzed repo context for chat: %s", repo_id)
        reply = await chat_with_repo(pre_analyzed, query, history)
        return {"reply": reply}

    # Fallback to understanding document
    cached = await db.repo_understandings.find_one(
        {"repo_id": repo_id}, {"_id": 0, "understanding": 1}
    )

    if not cached:
        logger.warning("No cached understanding for %s — triggering analysis", repo_id)
        await get_repo_summary(repo_id)
        cached = await db.repo_understandings.find_one(
            {"repo_id": repo_id}, {"_id": 0, "understanding": 1}
        )

    if not cached:
        raise ValueError(
            f"Could not build understanding for repository {repo_id}. "
            "Ensure the repository has been successfully imported before chatting."
        )

    reply = await chat_with_repo(cached["understanding"], query, history)
    return {"reply": reply}

async def invalidate_repo_cache(repo_id: str) -> None:
    db = get_db()
    await db.repo_understandings.delete_one({"repo_id": repo_id})
    await db.repo_chat_history.delete_one({"repo_id": repo_id})
    logger.info("Invalidated understanding cache and chat history for repo %s", repo_id)
