from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.ml.embeddings import embed_texts                # <— this path!
from app.adapters.vector.weaviate_investors import insert_investor
from app.api.v1.schemas import IngestResponse

router = APIRouter(prefix="/ingest/investors", tags=["ingest-investors"])

class InvestorList(BaseModel):
    items: List[Dict[str, Any]]

@router.post("/json", response_model=IngestResponse)
def ingest_investors_json(payload: InvestorList):
    items = payload.items or []
    if not items:
        raise HTTPException(400, "No investors provided.")
    texts = [" | ".join([
        i.get("name",""), i.get("sectors",""), i.get("stages",""),
        i.get("geo",""), i.get("checkSize",""), i.get("thesis",""), i.get("constraints","")
    ]) for i in items]
    vecs = embed_texts(texts)
    for i, v in zip(items, vecs):
        insert_investor(i, v)
    return IngestResponse(inserted=len(items))