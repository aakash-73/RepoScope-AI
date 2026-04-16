import asyncio
import logging
from database import get_db
from services.groq_service import explain_component
from services.analyzer_service import analyze_file

logger = logging.getLogger(__name__)

async def analyze_all_files(repo_id: str):
    """
    Background task to analyze every file in a repository sequentially.
    Stores results in db.file_explanations.
    """
    db = get_db()
    
    logger.info("Starting bulk analysis for repo %s", repo_id)
    
    # Fetch all files for this repo
    cursor = db.files.find({"repo_id": repo_id})
    files = await cursor.to_list(length=None)
    
    if not files:
        logger.warning("No files found for bulk analysis in repo %s", repo_id)
        return

    for i, file_doc in enumerate(files):
        path = file_doc["path"]
        
        # Check if already analyzed (unless we want to force refresh)
        existing = await db.file_explanations.find_one({"repo_id": repo_id, "path": path})
        if existing:
            logger.debug("Skipping already analyzed file: %s", path)
            continue
            
        logger.info("[%d/%d] Analyzing file: %s", i + 1, len(files), path)
        
        try:
            # Re-run local analysis to get fresh imports/exports if needed
            # though they should already be in file_doc
            imports = file_doc.get("imports", [])
            
            # Call LLM to explain the component
            explanation = await explain_component(
                file_path=path,
                content=file_doc["content"],
                language=file_doc.get("language", "text"),
                imports=imports
            )
            
            # Save to DB
            await db.file_explanations.update_one(
                {"repo_id": repo_id, "path": path},
                {"$set": {
                    "repo_id":     repo_id,
                    "path":        path,
                    "explanation": explanation,
                    "dependencies": imports[:30],
                }},
                upsert=True
            )
            
            # Subtle delay to avoid aggressive rate limiting even though it's sequential
            await asyncio.sleep(0.5) 
            
        except Exception as e:
            logger.error("Failed to analyze file %s in bulk: %s", path, e)
            # Continue with next file instead of aborting entirely
            continue

    logger.info("Finished bulk analysis for repo %s", repo_id)

def trigger_bulk_analysis(repo_id: str):
    """
    Utility to fire-and-forget the bulk analysis task.
    """
    asyncio.create_task(analyze_all_files(repo_id))

