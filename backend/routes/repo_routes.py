# app/api/routes/repo_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from services.repo_service import create_repository

router = APIRouter()

class RepoRequest(BaseModel):
    github_url: str

@router.post("/repo/analyze")
async def analyze_repository(request: RepoRequest):
    """
    Endpoint to clone a repo, store it in MongoDB, and analyze files.
    """
    try:
        repo_id = await create_repository(request.github_url)
        return {
            "message": "Repository cloned and files stored successfully",
            "repo_id": repo_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

