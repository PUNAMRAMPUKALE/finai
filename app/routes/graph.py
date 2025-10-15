# app/routes/graph.py
# Purpose: endpoints to (a) build/sync KG from docs; (b) run Cypher queries.
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
from app.services.kg_builder import build_graph_from_docs
from app.services.neo4j_client import run_cypher

router = APIRouter(prefix="/graph", tags=["graph"])

class BuildResponse(BaseModel):
    inserted: int

@router.post("/sync", response_model=BuildResponse)
def sync_graph(max_docs: int = 200):
    
    count = build_graph_from_docs(max_docs)
    return BuildResponse(inserted=int(count or 0))

class CypherRequest(BaseModel):
    query: str
    params: Dict[str, Any] | None = None

@router.post("/query")
def query_graph(req: CypherRequest):
    try:
        rows = run_cypher(req.query, req.params or {})
        # Convert Neo4j Record -> dicts
        out = [dict(r) for r in rows]
        return {"rows": out}
    except Exception as e:
        raise HTTPException(400, f"Cypher error: {e}")
        
