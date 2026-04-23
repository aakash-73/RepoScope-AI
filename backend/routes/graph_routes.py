from fastapi import APIRouter, Query
from services.graph_aggregator_service import get_dual_view_graph

router = APIRouter()

@router.post("/repo/{repo_id}/build-graph")
async def generate_graph(repo_id: str, view_type: str = Query("structure")):
    graph = await get_dual_view_graph(repo_id, view_type)
    return graph

