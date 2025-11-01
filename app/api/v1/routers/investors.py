from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
import os

from app.deps import get_current_user   # ← unified import
from app.adapters.vector.weaviate_client import get_client, INVESTOR
from app.db.models import Investor, QAResponse
from app.db.core import get_session

# -----------------------------------------------------------------------------
# Router must be defined BEFORE using it in decorators
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/investors", tags=["investors"])

# -----------------------------------------------------------------------------
# Simple list endpoint (DB only)
# -----------------------------------------------------------------------------
@router.get("/", response_model=list[Investor])
def list_investors(db: Session = Depends(get_session)):
    return db.exec(select(Investor)).all()

# -----------------------------------------------------------------------------
# Optional RAG helper
# -----------------------------------------------------------------------------
try:
    from app.adapters.vector.weaviate_investors import rag_docs_for_investor
except Exception:
    def rag_docs_for_investor(name: str, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return []

# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class AnalyzeReq(BaseModel):
    name: str
    pitch_summary: Optional[str] = ""

class QAReq(BaseModel):
    name: str
    question: str
    pitch_summary: Optional[str] = ""

class IngestReq(BaseModel):
    names: Optional[List[str]] = None  # if None, pull a page from Weaviate

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _get_investor_object_by_name(name: str) -> Dict[str, Any]:
    client = get_client()
    coll = client.collections.get(INVESTOR)

    # Try BM25 exact-ish match
    try:
        res = coll.query.bm25(query=name, limit=5)
        cand = None
        for o in (res.objects or []):
            if not o or not o.properties:
                continue
            if str(o.properties.get("name", "")).strip().lower() == name.strip().lower():
                cand = o
                break
        cand = cand or (res.objects[0] if res.objects else None)
        if cand:
            return cand.properties or {}
    except Exception:
        pass

    # Fallback enumerate
    try:
        res = coll.query.fetch_objects(limit=50)
        for o in (res.objects or []):
            props = o.properties or {}
            if str(props.get("name", "")).strip().lower() == name.strip().lower():
                return props
        if res.objects:
            return res.objects[0].properties or {}
    except Exception:
        pass

    return {}

def _split_csvlike(s: str) -> List[str]:
    return [p.strip() for p in (s or "").replace("•", ",").replace("|", ",").split(",") if p.strip()]

def _contains_any(text: str, candidates: List[str]) -> bool:
    t = (text or "").lower()
    return any(c and c.lower() in t for c in candidates)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.get("/{name}")
def get_investor(name: str, u=Depends(get_current_user), db: Session = Depends(get_session)):
    # Prefer DB; fall back to vector store
    inv_row: Optional[Investor] = db.exec(select(Investor).where(Investor.name == name)).first()
    if inv_row:
        return inv_row.dict()
    props = _get_investor_object_by_name(name)
    if not props:
        raise HTTPException(status_code=404, detail="Investor not found")
    return props

@router.post("/ingest")
def ingest_investors(req: IngestReq, u=Depends(get_current_user), db: Session = Depends(get_session)):
    """
    Sync investors from Weaviate into Postgres.
    - If req.names is provided, fetch those names.
    - Otherwise pull the first page.
    """
    client = get_client()
    coll = client.collections.get(INVESTOR)

    objects = []
    if req.names:
        for name in req.names:
            props = _get_investor_object_by_name(name)
            if props:
                objects.append(props)
    else:
        res = coll.query.fetch_objects(limit=200)
        for o in (res.objects or []):
            if o and o.properties:
                objects.append(o.properties)

    inserted = 0
    updated = 0
    for p in objects:
        name = (p.get("name") or "").strip()
        if not name:
            continue
        existing = db.exec(select(Investor).where(Investor.name == name)).first()
        if existing:
            existing.firm = p.get("firm") or existing.firm
            existing.sectors = p.get("sectors") or existing.sectors
            existing.stages = p.get("stages") or existing.stages
            existing.geo = p.get("geo") or existing.geo or p.get("geo_include")
            existing.check_min = p.get("check_min") or existing.check_min
            existing.check_max = p.get("check_max") or existing.check_max
            existing.check_currency = p.get("check_currency") or existing.check_currency
            existing.thesis = p.get("thesis") or existing.thesis
            existing.constraints = p.get("constraints") or existing.constraints
            updated += 1
        else:
            inv = Investor(
                name=name,
                firm=p.get("firm"),
                sectors=p.get("sectors"),
                stages=p.get("stages"),
                geo=p.get("geo") or p.get("geo_include"),
                check_min=p.get("check_min"),
                check_max=p.get("check_max"),
                check_currency=p.get("check_currency"),
                thesis=p.get("thesis"),
                constraints=p.get("constraints"),
                weaviate_id=p.get("id"),
            )
            db.add(inv)
            inserted += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflict while upserting investors")

    return {"inserted": inserted, "updated": updated, "total_seen": len(objects)}

@router.post("/analyze")
def analyze_investor(payload: AnalyzeReq, u=Depends(get_current_user), db: Session = Depends(get_session)):
    # prefer DB, fallback to vector
    inv_row = db.exec(select(Investor).where(Investor.name == payload.name)).first()
    inv = inv_row.dict() if inv_row else _get_investor_object_by_name(payload.name)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")

    pitch = payload.pitch_summary or ""
    sectors = _split_csvlike(inv.get("sectors", ""))
    stages  = _split_csvlike(inv.get("stages", ""))
    geos    = _split_csvlike(inv.get("geo", "") or inv.get("geo_include", ""))

    sec_hit = _contains_any(pitch, sectors) or not sectors
    stg_hit = _contains_any(pitch, stages) or not stages
    geo_hit = _contains_any(pitch, geos) or not geos

    sec_bullets = [f"Investor sectors: {', '.join(sectors)}" or "Investor sectors: —"]
    sec_bullets.append("Your pitch mentions these sectors." if sec_hit else "Your pitch doesn’t clearly mention these sectors.")
    stg_bullets = [f"Investor stages: {', '.join(stages)}" or "Investor stages: —"]
    stg_bullets.append("Stage alignment looks reasonable." if stg_hit else "Stage alignment is unclear.")
    geo_bullets = [f"Investor geographies: {', '.join(geos)}" or "Investor geographies: —"]
    geo_bullets.append("Geography looks compatible." if geo_hit else "Geography alignment is unclear.")

    hits = [sec_hit, stg_hit, geo_hit]
    score_hint = int(round(100 * (sum(1 for h in hits if h) / max(1, len(hits)))))

    snippets = []
    for key in ["thesis", "constraints", "checkSize", "ownership_target", "lead_follow"]:
        val = (inv.get(key) or "").strip()
        if val:
            snippets.append({"text": f"{key.replace('_',' ').title()}: {val}", "score": 1.0})

    agents = [
        {"agent": "SectorAgent", "summary": "Checks sector alignment", "bullets": sec_bullets},
        {"agent": "StageAgent",  "summary": "Checks fundraising stage alignment", "bullets": stg_bullets},
        {"agent": "GeoAgent",    "summary": "Checks geography alignment", "bullets": geo_bullets},
    ]

    return {"context_snippets": snippets, "agents": agents, "score_hint": score_hint}

def _build_context(inv: Dict[str, Any], pitch_summary: str, question: str) -> str:
    fields = [
        ("Name", inv.get("name", "")),
        ("Firm", inv.get("firm", "")),
        ("Sectors", inv.get("sectors", "")),
        ("Stages", inv.get("stages", "")),
        ("Geography", inv.get("geo", "") or inv.get("geo_include", "")),
        ("Check Size", inv.get("checkSize", "") or f"{inv.get('check_min','')} - {inv.get('check_max','')}".strip(" -")),
        ("Thesis", inv.get("thesis", "")),
        ("Constraints", inv.get("constraints", "")),
    ]
    parts = [f"{k}: {v}" for k, v in fields if v]
    try:
        chunks = rag_docs_for_investor(inv.get("name", ""), question, top_k=3)
    except Exception:
        chunks = []
    if chunks:
        parts.append("Sources:\n" + "\n".join(f"- {c.get('title','')}: {c.get('text','')[:300]}" for c in chunks))
    if pitch_summary:
        parts.append(f"Pitch Summary: {pitch_summary[:600]}")
    return "\n".join(parts)

def _mock_answer(inv: Dict[str, Any], q: str, context: str) -> str:
    ql = q.lower()
    sectors = inv.get("sectors") or "—"
    stages  = inv.get("stages") or "—"
    geo     = inv.get("geo") or inv.get("geo_include") or "—"
    check   = inv.get("checkSize") or f"{inv.get('check_min','')} - {inv.get('check_max','')}".strip(" -") or "—"
    thesis  = inv.get("thesis") or "—"

    if "thesis" in ql or "align" in ql or "type of startups" in ql:
        return f"They typically back startups aligned with: {thesis}. Focus sectors: {sectors}."
    if "fit" in ql or "focus areas" in ql:
        return f"Fit = sector({sectors}), stage({stages}), geo({geo}). Emphasize traction and why-now."
    if "sector" in ql or "technolog" in ql:
        return f"Preferred sectors/technologies: {sectors}."
    if "regional" in ql or "geograph" in ql or "global" in ql:
        return f"Regional focus: {geo}."
    if "check" in ql or "size" in ql:
        return f"Typical check size: {check}. Stage focus: {stages}."
    return f"Sectors: {sectors}\nStages: {stages}\nGeo: {geo}\nCheck: {check}\nThesis: {thesis}"

def _maybe_llm_answer(question: str, context: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": f"Question:\n{question}\n\nContext:\n{context}"}],
            temperature=0.2,
            max_tokens=350,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print("LLM error:", e)
        return None

@router.post("/qa")
def qa_investor(payload: QAReq, u=Depends(get_current_user), db: Session = Depends(get_session)):
    # prefer DB; fallback to vector
    inv_row = db.exec(select(Investor).where(Investor.name == payload.name)).first()
    inv = inv_row.dict() if inv_row else _get_investor_object_by_name(payload.name)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")

    q = (payload.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question is required")

    context = _build_context(inv, payload.pitch_summary or "", q)
    answer = _maybe_llm_answer(q, context) or _mock_answer(inv, q, context)

    # persist QA
    db.add(QAResponse(investor_name=inv.get("name") or payload.name, user_id=u.id, question=q, answer=answer))
    db.commit()

    return {"answer": answer}