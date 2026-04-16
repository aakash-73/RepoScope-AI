from fastapi import APIRouter
from services.graph_service import build_dependency_graph

router = APIRouter()

@router.post("/repo/{repo_id}/build-graph")
async def generate_graph(repo_id: str):
    graph = await build_dependency_graph(repo_id)
    return graph

