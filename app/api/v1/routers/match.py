from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from typing import Optional, Dict, Any, List
from app.api.v1.schemas import InvestorList, IngestResponse, MatchResponse
from app.utils.pdf_loader import pdf_to_text
from app.ml.embeddings import embed_texts, embed_text
from app.adapters.vector.weaviate_investors import insert_investor, search_similar_investors
from .auth import get_current_user

router = APIRouter(prefix="", tags=["match"])

# --- (Optional) Ingest investors via JSON so you have a corpus to match against ---
@router.post("/ingest/investors/json", response_model=IngestResponse)
def ingest_investors(payload: InvestorList, u=Depends(get_current_user)):
    items = payload.items or []
    if not items:
        raise HTTPException(400, "No investors provided.")
    # build texts for embedding
    texts = [" | ".join([
        i.get("name",""), i.get("sectors",""), i.get("stages",""),
        i.get("geo",""), i.get("checkSize",""), i.get("thesis",""), i.get("constraints","")
    ]) for i in items]
    vecs = embed_texts(texts)
    for item, vec in zip(items, vecs):
        insert_investor(item, vec)
    return IngestResponse(inserted=len(items))

# --- Upload a startup pitch PDF and get matched investors ---
@router.post("/match/pitch", response_model=MatchResponse)
async def match_pitch_pdf(
    file: UploadFile = File(...),
    sector: Optional[str] = Form(None),
    stage: Optional[str]  = Form(None),
    geo: Optional[str]    = Form(None),
    traction: Optional[str] = Form(None),
    top_n: int = Form(6),
    u=Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    text = pdf_to_text(content)

    # Build a compact query text (metadata + pitch snippet)
    query_text = " | ".join([
        sector or "", stage or "", geo or "", traction or "",
        (text or "")[:1200]  # cap length for speed
    ]).strip()

    qv = embed_text(query_text)
    hits = search_similar_investors(qv, limit=top_n)

    return MatchResponse(matches=hits)
