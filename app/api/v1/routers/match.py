# app/api/v1/routers/match.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pathlib import Path
import os, uuid, re
from collections import Counter

from sqlmodel import Session, select

from .auth import get_current_user
from app.db.core import get_session
from app.db.models import Pitch, Match, Investor
from app.utils.pdf_loader import pdf_to_text, PdfExtractError

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/match", tags=["match"])

def _tokenize(s: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", (s or "").lower())

def _score_investor(pitch_text: str, inv: Investor) -> float:
    """
    Very simple DB-only scoring:
    - +1 per unique sector word match
    - +1 per unique stage word match
    - +1 per unique geo word match
    - + up to +2 for keyword overlap between pitch and (thesis|constraints)
    """
    pitch_toks = set(_tokenize(pitch_text))
    score = 0.0

    def uniq_hits(field: Optional[str]) -> int:
        if not field:
            return 0
        words = set(_tokenize(field.replace(",", " ")))
        return len(words & pitch_toks)

    score += min(3, uniq_hits(inv.sectors))     # cap each bucket so it doesn't explode
    score += min(2, uniq_hits(inv.stages))
    score += min(2, uniq_hits(inv.geo))
    thesis_hits = uniq_hits(inv.thesis)
    const_hits  = uniq_hits(inv.constraints)
    score += min(2, thesis_hits + const_hits)

    return score

def _build_card(inv: Investor, score: float) -> Dict[str, Any]:
    # Normalize to a 0–100 hint (optional, just for UI continuity)
    score_pct = int(max(0, min(100, round(100 * score / 9.0))))
    return {
        "name": inv.name,
        "firm": inv.firm,
        "sectors": inv.sectors,
        "stages": inv.stages,
        "geo": inv.geo,
        "check_min": inv.check_min,
        "check_max": inv.check_max,
        "check_currency": inv.check_currency,
        "thesis": inv.thesis,
        "constraints": inv.constraints,
        "score_pct": score_pct,
        "distance": None,  # legacy field for UI; not meaningful in DB-only mode
    }

@router.post("/pitch")
async def recommend_pitch(
    file: UploadFile = File(...),
    top_n: int = Form(default=10),
    # optional form hints (ignored by scorer, but you can weave them in if you want)
    sector: Optional[str]   = Form(default=None),
    stage: Optional[str]    = Form(default=None),
    geo: Optional[str]      = Form(default=None),
    traction: Optional[str] = Form(default=None),

    u = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        content = await file.read()
        text = pdf_to_text(content)
    except PdfExtractError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    if not text:
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    # Save uploaded file (optional)
    rid = uuid.uuid4().hex[:8]
    saved_path = str(UPLOAD_DIR / f"{rid}_{file.filename}")
    try:
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception:
        saved_path = ""

    # Persist pitch
    pitch_row = Pitch(user_id=u.id, file_path=saved_path, summary=text)
    db.add(pitch_row)
    db.commit()
    db.refresh(pitch_row)

    # DB-only search: pull investors and score
    investors = db.exec(select(Investor)).all()
    scored = [(_build_card(inv, _score_investor(text, inv)), inv) for inv in investors]
    scored.sort(key=lambda x: x[0]["score_pct"], reverse=True)
    hits = [s for s, _inv in scored[:max(1, top_n)] if s["score_pct"] > 0]

    # Persist matches (for what we returned)
    for h in hits:
        db.add(Match(
            pitch_id=pitch_row.id,
            investor_name=h.get("name") or "",
            score_pct=int(h.get("score_pct") or 0),
            distance=h.get("distance"),
        ))
    db.commit()

    # Return DB-derived matches only
    return {"matches": hits, "query_text": text[:3000]}