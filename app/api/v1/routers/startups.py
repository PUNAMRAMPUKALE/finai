from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.ml.embeddings import embed_texts                # <— this path!
from app.adapters.vector.weaviate_startups import insert_startup
from app.api.v1.schemas import IngestResponse

router = APIRouter(prefix="/ingest/startups", tags=["ingest-startups"])

class StartupList(BaseModel):
    items: List[Dict[str, Any]]

@router.post("/json", response_model=IngestResponse)
def ingest_startups_json(payload: StartupList):
    items = payload.items or []
    if not items:
        raise HTTPException(400, "No startups provided.")
    texts = [" | ".join([
        s.get("name",""), s.get("sector",""), s.get("stage",""),
        s.get("geo",""), s.get("traction",""), s.get("description","")
    ]) for s in items]
    vecs = embed_texts(texts)
    for s, v in zip(items, vecs):
        insert_startup(s, v)
    return IngestResponse(inserted=len(items))