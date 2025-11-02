from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pathlib import Path
import os, uuid, re

from sqlmodel import Session, select

from app.deps import get_current_user
from app.db.core import get_session
from app.db.models import Pitch, Match, Investor
from app.utils.pdf_loader import pdf_to_text, PdfExtractError

# NEW: embeddings + vector search
from app.ml.embeddings import embed_text
from app.adapters.vector.weaviate_investors import search_similar_investors

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/match", tags=["match"])

def _tokenize(s: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", (s or "").lower())

def _score_investor_db(pitch_text: str, inv: Investor) -> float:
    """
    Very simple DB-only scoring:
    - +1 per unique sector word match
    - +1 per unique stage word match
    - +1 per unique geo word match
    - + up to +2 for keyword overlap between pitch and (thesis|constraints)
    Max ≈ 9 points → we normalize later to 0..100.
    """
    pitch_toks = set(_tokenize(pitch_text))
    score = 0.0

    def uniq_hits(field: Optional[str]) -> int:
        if not field:
            return 0
        words = set(_tokenize(field.replace(",", " ")))
        return len(words & pitch_toks)

    score += min(3, uniq_hits(inv.sectors))
    score += min(2, uniq_hits(inv.stages))
    score += min(2, uniq_hits(inv.geo))
    thesis_hits = uniq_hits(inv.thesis)
    const_hits  = uniq_hits(inv.constraints)
    score += min(2, thesis_hits + const_hits)

    return score

def _norm_db_score(score: float) -> int:
    # Normalize to a 0–100 hint (cap denominator to the same 9 points)
    return int(max(0, min(100, round(100 * score / 9.0))))

def _blend_scores(db_pct: Optional[int], vec_pct: Optional[int]) -> int:
    """
    Weighted blend (deterministic):
    - If both present: 0.4 * DB + 0.6 * Vector
    - If only one present: return it
    """
    if db_pct is None and vec_pct is None:
        return 0
    if db_pct is None:
        return int(vec_pct or 0)
    if vec_pct is None:
        return int(db_pct or 0)
    return int(round(0.4 * db_pct + 0.6 * vec_pct))

def _build_card_from_db(inv: Investor, db_score_pct: int) -> Dict[str, Any]:
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
        "score_pct": db_score_pct,
        "distance": None,
    }

@router.post("/pitch")
async def recommend_pitch(
    file: UploadFile = File(...),
    top_n: int = Form(default=10),

    # optional hints (currently unused in scorer but available)
    sector: Optional[str]   = Form(default=None),
    stage: Optional[str]    = Form(default=None),
    geo: Optional[str]      = Form(default=None),
    traction: Optional[str] = Form(default=None),

    u = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # ---- Read / persist pitch
    try:
        content = await file.read()
        text = pdf_to_text(content)
    except PdfExtractError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    if not text:
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    rid = uuid.uuid4().hex[:8]
    saved_path = str(UPLOAD_DIR / f"{rid}_{file.filename}")
    try:
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception:
        saved_path = ""

    pitch_row = Pitch(user_id=u.id, file_path=saved_path, summary=text)
    db.add(pitch_row)
    db.commit()
    db.refresh(pitch_row)

    # ---- DB scoring
    investors = db.exec(select(Investor)).all()
    db_scores: Dict[str, Dict[str, Any]] = {}
    for inv in investors:
        db_pct = _norm_db_score(_score_investor_db(text, inv))
        if db_pct > 0:
            db_scores[inv.name] = {
                "card": _build_card_from_db(inv, db_pct),
                "db_pct": db_pct,
            }

    # ---- Vector scoring (Weaviate)
    vector_hits: Dict[str, Dict[str, Any]] = {}
    try:
        pitch_vec = embed_text(text[:4000])  # keep it bounded & deterministic
        vec_results = search_similar_investors(pitch_vec, limit=max(20, top_n * 2))
        for r in vec_results:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            vector_hits[name] = {
                "vec_pct": int(r.get("score_pct") or 0),
                "distance": r.get("distance"),
                "raw": r,
            }
    except Exception:
        # Weaviate not available or vector step failed → just skip vector side
        vec_results = []

    # ---- Merge & blend (deterministic)
    merged: Dict[str, Dict[str, Any]] = {}

    # Seed with DB cards
    for name, item in db_scores.items():
        merged[name] = {
            "name": name,
            "card": item["card"],
            "db_pct": item["db_pct"],
            "vec_pct": None,
            "distance": None,
        }

    # Merge vector data, create new cards when investor not in DB (rare)
    for name, v in vector_hits.items():
        if name in merged:
            merged[name]["vec_pct"] = v["vec_pct"]
            merged[name]["distance"] = v["distance"]
        else:
            # create a minimal card from vector properties if DB didn’t have it
            r = v["raw"]
            card = {
                "name": r.get("name"),
                "firm": r.get("firm"),
                "sectors": r.get("sectors"),
                "stages": r.get("stages"),
                "geo": r.get("geo"),
                "check_min": r.get("check_min"),
                "check_max": r.get("check_max"),
                "check_currency": r.get("check_currency"),
                "thesis": r.get("thesis"),
                "constraints": r.get("constraints"),
                "score_pct": 0,   # temporary; set after blending
                "distance": v["distance"],
            }
            merged[name] = {
                "name": name,
                "card": card,
                "db_pct": None,
                "vec_pct": v["vec_pct"],
                "distance": v["distance"],
            }

    # Compute final blended score and finalize cards
    cards: List[Dict[str, Any]] = []
    for name, m in merged.items():
        final_pct = _blend_scores(m.get("db_pct"), m.get("vec_pct"))
        card = dict(m["card"])
        card["score_pct"] = final_pct
        card["distance"] = m.get("distance")
        cards.append(card)

    # Sort by blended score, tie-breaker: lower distance if available
    cards.sort(key=lambda c: (-int(c.get("score_pct") or 0), float(c["distance"]) if c.get("distance") is not None else 9e9))

    hits = [c for c in cards[:max(1, top_n)] if int(c.get("score_pct") or 0) > 0]

    # ---- Persist matches (what we returned)
    for h in hits:
        db.add(Match(
            pitch_id=pitch_row.id,
            investor_name=h.get("name") or "",
            score_pct=int(h.get("score_pct") or 0),
            distance=h.get("distance"),
        ))
    db.commit()

    return {"matches": hits, "query_text": text[:3000]}