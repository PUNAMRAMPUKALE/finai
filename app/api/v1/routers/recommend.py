# app/api/v1/routers/recommend.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.domain.services.recommendation import recommend, recommend_from_pitch
from app.utils.pdf_loader import pdf_to_text  # uses PyPDF2/pypdf
from app.api.v1.schemas import RecommendRequest, RecommendResponse  # if you have them

# router = APIRouter(prefix="/api/v1/recommend", tags=["recommend"])
# from fastapi import APIRouter
router = APIRouter(prefix="/recommend", tags=["recommend"])
# --- existing JSON profile->products endpoint (keep yours if already present) ---
class ProfileReq(BaseModel):
    profile: Dict[str, Any]
    mode: Optional[str] = "profile->products"
    candidate_k: Optional[int] = 20
    top_n: Optional[int] = 5
    explain: Optional[bool] = True

@router.post("", response_model=Dict[str, Any])
def recommend_api(req: ProfileReq):
    return recommend(
        req.profile,
        mode=req.mode or "profile->products",
        candidate_k=req.candidate_k or 20,
        top_n=req.top_n or 5,
        explain=req.explain if req.explain is not None else True,
    )

# --- NEW: upload pitch PDF -> investor matches ---
@router.post("/pitch/file", response_model=Dict[str, Any])
async def recommend_pitch_file(
    file: UploadFile = File(...),
    sector: Optional[str] = Form(None),
    stage: Optional[str] = Form(None),
    geo: Optional[str] = Form(None),
    traction: Optional[str] = Form(None),
    top_n: int = Form(6),
    candidate_k: int = Form(30),
    explain: bool = Form(True),
):
    try:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        # Save to a temp path then extract (or read bytes → pdf_to_text if you support streams)
        contents = await file.read()
        # Write to tmp so pdf_to_text can open
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            pitch_text = pdf_to_text(tmp_path)
        finally:
            os.unlink(tmp_path)

        meta = {k: v for k, v in {
            "sector": sector, "stage": stage, "geo": geo, "traction": traction
        }.items() if v}

        return recommend_from_pitch(
            pitch_text=pitch_text,
            meta=meta,
            candidate_k=candidate_k,
            top_n=top_n,
            explain=explain,
        )
    except HTTPException:
        raise
    except Exception as e:
        # Don't crash the connection; return 500 JSON instead of killing socket
        raise HTTPException(status_code=500, detail=f"pitch/file failed: {e}")