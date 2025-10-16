# app/api/v1/routers/graph.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from app.domain.services.kg_builder import build_graph_from_docs          # ✅ moved
from app.adapters.graph.neo4j_client import run_cypher                    # ✅ moved

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
        out = [dict(r) for r in rows]
        return {"rows": out}
    except Exception as e:
        raise HTTPException(400, f"Cypher error: {e}")