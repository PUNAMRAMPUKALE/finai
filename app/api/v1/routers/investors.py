# app/api/v1/routers/investors.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# ✅ FIX: import from sibling module in the same 'routers' package
from .auth import get_current_user
from app.adapters.vector.weaviate_client import get_client, INVESTOR
from app.ml.embeddings import embed_text
# (and whatever else you import below)


router = APIRouter(prefix="/investors", tags=["investors"])

# ---------- Pydantic Schemas ----------
class AnalyzeReq(BaseModel):
    name: str
    pitch_summary: Optional[str] = ""

class QAReq(BaseModel):
    name: str
    question: str
    pitch_summary: Optional[str] = ""

# ---------- Helpers ----------
def _get_investor_object_by_name(name: str) -> Dict[str, Any]:
    """
    Try to fetch an investor by name using BM25; fall back to scanning (tiny demo corpuses are fine).
    """
    client = get_client()
    coll = client.collections.get(INVESTOR)

    # First: BM25 (text search)
    try:
        res = coll.query.bm25(query=name, limit=5)
        best = None
        for o in res.objects or []:
            if not o or not o.properties: 
                continue
            if str(o.properties.get("name", "")).strip().lower() == name.strip().lower():
                best = o
                break
        if not best and res.objects:
            best = res.objects[0]
        if best:
            return best.properties or {}
    except Exception:
        pass

    # Fallback: fetch a handful and do a simple compare
    try:
        res = coll.query.fetch_objects(limit=50)
        for o in res.objects or []:
            props = (o.properties or {})
            if str(props.get("name", "")).strip().lower() == name.strip().lower():
                return props
        if res.objects:
            return res.objects[0].properties or {}
    except Exception:
        pass

    return {}

def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _contains_any(text: str, candidates: List[str]) -> bool:
    t = text.lower()
    return any(c.lower() in t for c in candidates if c)

def _split_csvlike(s: str) -> List[str]:
    return [p.strip() for p in (s or "").replace("•", ",").replace("|", ",").split(",") if p.strip()]

# ---------- Routes ----------
@router.get("/{name}")
def get_investor(name: str, u=Depends(get_current_user)):
    props = _get_investor_object_by_name(name)
    if not props:
        raise HTTPException(status_code=404, detail="Investor not found")
    return props

@router.post("/analyze")
def analyze_investor(payload: AnalyzeReq, u=Depends(get_current_user)):
    """
    Very lightweight 'multi-agent' analysis:
      - SectorAgent checks sector overlap
      - StageAgent checks stage overlap
      - GeoAgent checks geo overlap
    Produces a score_hint and small bullet summaries.
    """
    inv = _get_investor_object_by_name(payload.name)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")

    pitch = payload.pitch_summary or ""
    sectors = _split_csvlike(inv.get("sectors", ""))
    stages  = _split_csvlike(inv.get("stages", ""))
    geos    = _split_csvlike(inv.get("geo", ""))

    # Agent 1: Sector
    sec_hit = _contains_any(pitch, sectors) or not sectors
    sec_bullets = []
    if sectors:
        sec_bullets.append(f"Investor sectors: {', '.join(sectors)}")
    if sec_hit:
        sec_bullets.append("Your pitch mentions one or more of these sectors.")
    else:
        sec_bullets.append("Your pitch doesn't clearly mention these sectors.")

    # Agent 2: Stage
    stg_hit = _contains_any(pitch, stages) or not stages
    stg_bullets = []
    if stages:
        stg_bullets.append(f"Investor stages: {', '.join(stages)}")
    if stg_hit:
        stg_bullets.append("Stage alignment looks reasonable.")
    else:
        stg_bullets.append("Stage alignment is unclear from your summary.")

    # Agent 3: Geo
    geo_hit = _contains_any(pitch, geos) or not geos
    geo_bullets = []
    if geos:
        geo_bullets.append(f"Investor geographies: {', '.join(geos)}")
    if geo_hit:
        geo_bullets.append("Geography looks compatible.")
    else:
        geo_bullets.append("Geography alignment is unclear.")

    hits = [sec_hit, stg_hit, geo_hit]
    score_hint = int(round(100 * (sum(1 for h in hits if h) / max(1, len(hits)))))

    # A couple of tiny 'context' snippets from the investor object
    snippets = []
    for key in ["thesis", "constraints", "checkSize"]:
        val = _norm(inv.get(key))
        if val:
            snippets.append({"text": f"{key.capitalize()}: {val}", "score": 1.0})

    agents = [
        {"agent": "SectorAgent", "summary": "Checks sector alignment", "bullets": sec_bullets},
        {"agent": "StageAgent",  "summary": "Checks fundraising stage alignment", "bullets": stg_bullets},
        {"agent": "GeoAgent",    "summary": "Checks geography alignment", "bullets": geo_bullets},
    ]

    return {
        "context_snippets": snippets,
        "agents": agents,
        "score_hint": score_hint,
    }

@router.post("/qa")
def qa_investor(payload: QAReq, u=Depends(get_current_user)):
    """
    Simple 'RAG' over the investor record + pitch summary.
    For demo purposes we craft a direct answer using known fields.
    """
    inv = _get_investor_object_by_name(payload.name)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")

    q = (payload.question or "").lower()
    sectors = inv.get("sectors", "")
    stages  = inv.get("stages", "")
    geo     = inv.get("geo", "")
    check   = inv.get("checkSize", "")
    thesis  = inv.get("thesis", "")
    cons    = inv.get("constraints", "")

    # Super light 'routing' by keywords – good enough for UI answers
    if "thesis" in q or "align" in q or "type of startups" in q:
        ans = (
            f"{inv.get('name','This investor')} typically backs startups aligned with its thesis: {thesis or '—'}.\n"
            f"Preferred sectors: {sectors or '—'}. Stages: {stages or '—'}. Geography: {geo or '—'}."
        )
    elif "fit" in q or "focus areas" in q:
        ans = (
            "Your fit is assessed across sector, stage and geography. "
            f"This investor mentions sectors [{sectors or '—'}], stages [{stages or '—'}], and regions [{geo or '—'}]. "
            "Emphasize the overlaps from your pitch (traction, ICP, and market proof)."
        )
    elif "sector" in q or "technology" in q or "tech" in q:
        ans = f"Preferred sectors/technologies: {sectors or '—'}. Thesis highlights: {thesis or '—'}."
    elif "regional" in q or "geograph" in q or "global" in q:
        ans = f"Regional focus: {geo or '—'}. They are generally open if the team/traction matches the thesis."
    elif "check" in q or "size" in q:
        ans = f"Typical check size: {check or '—'}. Stage focus: {stages or '—'}."
    else:
        # Generic fallback answer
        ans = (
            f"Here are the core details:\n"
            f"- Sectors: {sectors or '—'}\n- Stages: {stages or '—'}\n- Geography: {geo or '—'}\n"
            f"- Check size: {check or '—'}\n- Thesis: {thesis or '—'}\n- Constraints: {cons or '—'}\n\n"
            "If you share more specifics from your pitch, I can tailor the answer further."
        )

    return {"answer": ans}
