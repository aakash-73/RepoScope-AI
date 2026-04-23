import os
import logging
from typing import Dict, List, Optional
from database import get_db

logger = logging.getLogger(__name__)

async def get_dual_view_graph(repo_id: str, view_type: str = "structure") -> dict:
    """
    Fetches graph data from MongoDB based on the requested view.
    'structure' -> Standard file dependency graph.
    'semantic' -> Knowledge Graph with category hubs and semantic clusters.
    """
    db = get_db()
    
    if view_type == "structure":
        # We can reuse the existing logic or fetch directly from files collection
        from services.graph_builder import build_dependency_graph
        cursor = db.files.find({"repo_id": repo_id})
        files = await cursor.to_list(length=None)
        return await build_dependency_graph(files, repo_id)
        
    elif view_type == "semantic":
        # Fetch knowledge graph: File nodes + Category/Role hubs
        nodes_cursor = db.kg_nodes.find({"repo_id": repo_id})
        kg_nodes = await nodes_cursor.to_list(length=None)
        
        edges_cursor = db.kg_edges.find({
            "repo_id": repo_id,
            "relation": {"$in": ["belongs_to", "has_role", "implements"]}
        })
        kg_edges = await edges_cursor.to_list(length=None)
        
        # Format for React Flow
        formatted_nodes = []
        for n in kg_nodes:
            node_id = n["id"].replace("/", "__").replace(".", "_")
            node_type = "codeNode" if n["type"] == "file" else "hubNode"
            
            # Map types to specific colors
            color_map = {
                "file": "#374151",
                "category": "#3B82F6", # Blue
                "role": "#8B5CF6",     # Purple
                "pattern": "#10B981"   # Green
            }
            
            formatted_nodes.append({
                "id": node_id,
                "type": node_type,
                "position": {"x": 0, "y": 0},
                "data": {
                    "label": n["label"],
                    "file_path": n["id"] if n["type"] == "file" else "",
                    "kind": n["type"],
                    "node_color": color_map.get(n["type"], "#B6FF3B"),
                    "language": "text",
                    "properties": n.get("properties", {})
                }
            })
            
        formatted_edges = []
        for e in kg_edges:
            sid = e["source"].replace("/", "__").replace(".", "_")
            tid = e["target"].replace("/", "__").replace(".", "_")
            formatted_edges.append({
                "id": f"e_{sid}_{tid}_{e['relation']}",
                "source": sid,
                "target": tid,
                "label": e["relation"],
                "animated": True if e["relation"] != "imports" else False,
                "style": {"stroke": "#B6FF3B", "strokeWidth": 1.5},
                "data": {"relation": e["relation"]}
            })
            
        return {
            "repo_id": repo_id,
            "nodes": formatted_nodes,
            "edges": formatted_edges,
            "is_semantic": True
        }
    
    return {"nodes": [], "edges": []}
