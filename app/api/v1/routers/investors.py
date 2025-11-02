# app/api/v1/routers/investors.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
import re

# Use your single current-user helper (from auth router)
from .auth import get_current_user

from app.adapters.vector.weaviate_client import get_client, INVESTOR
from app.db.models import Investor, QAResponse
from app.db.core import get_session
from app.ml.embeddings import embed_texts, embed_text

router = APIRouter(prefix="/investors", tags=["investors"])

# =========================
# Utility helpers
# =========================

def _split_csvlike(s: str) -> List[str]:
    return [p.strip() for p in (s or "").replace("•", ",").replace("|", ",").split(",") if p.strip()]

def _contains_any(text: str, candidates: List[str]) -> bool:
    t = (text or "").lower()
    return any(c and c.lower() in t for c in candidates)

def _cos_sim(a, b):
    return sum(x * y for x, y in zip(a, b))

def split_paragraphs(text: str, max_len: int = 600) -> List[str]:
    if not text:
        return []
    raw = [p.strip() for p in text.replace("\r", "").split("\n") if p.strip()]
    out, buf = [], ""
    for p in raw:
        if len(buf) + 1 + len(p) < max_len:
            buf = (buf + " " + p).strip()
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out

def _tokenize(s: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", (s or "").lower())

def _kw_score(text: str, query: str) -> int:
    qt = set(_tokenize(query))
    tt = set(_tokenize(text))
    return len(qt & tt)

def retrieve(passages: List[str], query: str, top_k: int = 4) -> List[Tuple[str, float]]:
    """
    Try embedding-based ranking; if that fails (model not cached, offline, etc.),
    fall back to deterministic keyword-overlap ranking. Returns (text, score).
    """
    if not passages:
        return []
    try:
        qv = embed_text(query)
        p_vecs = embed_texts(passages)
        scored = [(p, _cos_sim(qv, pv)) for p, pv in zip(passages, p_vecs)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    except Exception:
        scored_kw = [(p, float(_kw_score(p, query))) for p in passages]
        scored_kw.sort(key=lambda x: x[1], reverse=True)
        return scored_kw[:top_k]

def _rank_with_fallback(cands: List[Tuple[str, Dict[str, Any]]], question: str, top_k: int) -> List[Dict[str, Any]]:
    """
    Rank candidate chunks using `retrieve` (embeddings → keyword fallback).
    Always returns <= top_k items with citation metadata.
    """
    if not cands:
        return []
    texts = [t for (t, _c) in cands]
    ranked_pairs = retrieve(texts, question, top_k=max(top_k, 6))  # over-retrieve a bit
    out: List[Dict[str, Any]] = []
    for text, score in ranked_pairs:
        for (ot, cite) in cands:
            if ot == text:
                out.append({"text": text, "score": float(score), "citation": cite})
                break
    return out[:top_k]

def _normalize_money(p: Dict[str, Any]) -> Dict[str, Any]:
    # If already normalized, return
    if ("check_min" in p) or ("check_max" in p) or ("check_currency" in p):
        return p
    legacy = (p.get("checkSize") or "").strip()
    if not legacy:
        return p
    mn, mx, cur = _parse_checksize(legacy)
    if mn is not None: p["check_min"] = mn
    if mx is not None: p["check_max"] = mx
    if cur: p["check_currency"] = cur
    return p

def _parse_checksize(s: str) -> tuple[Optional[float], Optional[float], Optional[str]]:
    ss = s.strip().upper()
    cur = None
    mcur = re.search(r"\b(USD|EUR|GBP|INR|CAD|AUD)\b", ss)
    if mcur:
        cur = mcur.group(1)
    clean = re.sub(r"[^\dKM\.–\-\,]", "", ss).replace("–", "-")
    parts = [p for p in re.split(r"-", clean) if p.strip()]
    def to_num(x: str) -> Optional[float]:
        x = x.replace(",", "").strip()
        mult = 1.0
        if x.endswith("M"):
            mult = 1_000_000.0; x = x[:-1]
        elif x.endswith("K"):
            mult = 1_000.0; x = x[:-1]
        try:
            return float(x) * mult
        except Exception:
            return None
    mn = to_num(parts[0]) if parts else None
    mx = to_num(parts[1]) if len(parts) > 1 else None
    return (mn, mx, cur or "USD")

def _get_investor_object_by_name(name: str) -> Dict[str, Any]:
    client = get_client()
    coll = client.collections.get(INVESTOR)

    # Try BM25 exact-ish first
    try:
        res = coll.query.bm25(query=name, limit=5)
        for o in (res.objects or []):
            props = o.properties or {}
            if str(props.get("name", "")).strip().lower() == name.strip().lower():
                return props
        if res.objects:
            return res.objects[0].properties or {}
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

# =========================
# Local request schemas
# =========================

class AnalyzeReq(BaseModel):
    name: str
    pitch_summary: str = Field(default="", alias="pitchSummary")
    class Config:
        populate_by_name = True

class QAReq(BaseModel):
    name: str
    question: str = Field(alias="questionText")
    pitch_summary: Optional[str] = Field(default="", alias="pitchSummary")
    mode: Optional[str] = "profile"  # "profile" or "fit"
    class Config:
        populate_by_name = True

class IngestReq(BaseModel):
    names: Optional[List[str]] = None

# =========================
# Routes
# =========================

@router.get("/", response_model=list[Investor])
def list_investors(db: Session = Depends(get_session)):
    return db.exec(select(Investor)).all()

@router.get("/{name}")
def get_investor(name: str, u=Depends(get_current_user), db: Session = Depends(get_session)):
    inv_row = db.exec(select(Investor).where(Investor.name == name)).first()
    if inv_row:
        return inv_row.dict()
    props = _get_investor_object_by_name(name)
    if not props:
        raise HTTPException(status_code=404, detail="Investor not found")
    return props

@router.post("/ingest")
def ingest_investors(req: IngestReq, u=Depends(get_current_user), db: Session = Depends(get_session)):
    client = get_client()
    coll = client.collections.get(INVESTOR)

    objects = []
    if req.names:
        for name in req.names:
            props = _get_investor_object_by_name(name)
            if props:
                objects.append(_normalize_money(props))
    else:
        res = coll.query.fetch_objects(limit=200)
        for o in (res.objects or []):
            if o and o.properties:
                objects.append(_normalize_money(o.properties))

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

# =========================
# Analyze (unchanged behavior)
# =========================

@router.post("/analyze")
def analyze_investor(payload: AnalyzeReq, u=Depends(get_current_user), db: Session = Depends(get_session)):
    inv_row = db.exec(select(Investor).where(Investor.name == payload.name)).first()
    inv = inv_row.dict() if inv_row else _get_investor_object_by_name(payload.name)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")

    inv = _normalize_money(inv)

    pitch = (payload.pitch_summary or "").strip()
    sectors = _split_csvlike(inv.get("sectors", ""))
    stages  = _split_csvlike(inv.get("stages", ""))
    geos    = _split_csvlike(inv.get("geo", "") or inv.get("geo_include", ""))

    sec_hit = _contains_any(pitch, sectors) or not sectors
    stg_hit = _contains_any(pitch, stages) or not stages
    geo_hit = _contains_any(pitch, geos) or not geos

    sec_bullets = [f"Investor sectors: {', '.join(sectors) or '—'}"]
    sec_bullets.append("Your pitch mentions these sectors." if sec_hit else "Your pitch doesn’t clearly mention these sectors.")

    stg_bullets = [f"Investor stages: {', '.join(stages) or '—'}"]
    stg_bullets.append("Stage alignment looks reasonable." if stg_hit else "Stage alignment is unclear.")

    geo_bullets = [f"Investor geographies: {', '.join(geos) or '—'}"]
    geo_bullets.append("Geography looks compatible." if geo_hit else "Geography alignment is unclear.")

    hits = [sec_hit, stg_hit, geo_hit]
    score_hint = int(round(100 * (sum(1 for h in hits if h) / max(1, len(hits)))))

    snippets = []
    if inv.get("check_min") or inv.get("check_max"):
        rng = f"{inv.get('check_min') or ''} - {inv.get('check_max') or ''}".strip(" -")
        snippets.append({"text": f"Check Size: {rng} {inv.get('check_currency','USD')}", "score": 1.0})

    for key in ["thesis", "constraints"]:
        val = (inv.get(key) or "").strip()
        if val:
            snippets.append({"text": f"{key.title()}: {val}", "score": 1.0})

    agents = [
        {"agent": "SectorAgent", "summary": "Checks sector alignment", "bullets": sec_bullets},
        {"agent": "StageAgent",  "summary": "Checks fundraising stage alignment", "bullets": stg_bullets},
        {"agent": "GeoAgent",    "summary": "Checks geography alignment", "bullets": geo_bullets},
    ]

    return {"context_snippets": snippets, "agents": agents, "score_hint": score_hint}

# =========================
# QA with modes + deterministic citations
# =========================

def _investor_chunks(inv: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """Return (text, citation) for investor-only fields."""
    inv = _normalize_money(inv)
    parts: List[Tuple[str, Dict[str, Any]]] = []

    def add(field: str, text: Optional[str]):
        t = (text or "").strip()
        if not t:
            return
        for ch in split_paragraphs(t, max_len=500):
            parts.append((ch, {"source": "investor", "title": inv.get("name", ""), "field": field}))

    money = None
    if inv.get("check_min") or inv.get("check_max"):
        rng = f"{inv.get('check_min') or ''} - {inv.get('check_max') or ''}".strip(" -")
        money = f"{rng} {inv.get('check_currency','USD')}"

    add("Sectors", inv.get("sectors"))
    add("Stages", inv.get("stages"))
    add("Geography", inv.get("geo") or inv.get("geo_include"))
    if money:
        add("Check Size", money)
    add("Thesis", inv.get("thesis"))
    add("Constraints", inv.get("constraints"))
    add("Profile", inv.get("profile"))

    return parts

def _pitch_chunks(pitch_summary: str) -> List[Tuple[str, Dict[str, Any]]]:
    if not pitch_summary:
        return []
    out: List[Tuple[str, Dict[str, Any]]] = []
    for ch in split_paragraphs(pitch_summary, max_len=500):
        out.append((ch, {"source": "pitch", "title": "Pitch Summary", "field": "pitch"}))
    return out

def _choose_mode(in_mode: Optional[str], question: str) -> str:
    m = (in_mode or "").strip().lower()
    if m in ("profile", "fit"):
        return m
    q = question.lower()
    if any(tok in q for tok in ["my startup", "our startup", "we ", "our ", "fit", "how do we", "how does my"]):
        return "fit"
    return "profile"

def _classify_intent(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in ["thesis", "type of startups", "best align"]):
        return "thesis"
    if any(k in ql for k in ["fit", "how does my", "how do we", "focus areas"]):
        return "fit"
    if any(k in ql for k in ["sector", "technology", "tech", "areas"]):
        return "sectors"
    if any(k in ql for k in ["regional", "geograph", "geo", "country", "global"]):
        return "geo"
    if any(k in ql for k in ["check", "size", "ticket"]):
        return "check"
    if "constraint" in ql or "avoid" in ql or "won't invest" in ql or "wont invest" in ql:
        return "constraints"
    if any(k in ql for k in ["due diligence", "diligence", "what will they ask"]):
        return "diligence"
    if any(k in ql for k in ["portfolio", "similar startups", "references", "intro path"]):
        return "portfolio"
    return "general"

def _compose_answer(inv: Dict[str, Any], mode: str, intent: str, snippets: List[Dict[str, Any]], pitch_summary: str) -> str:
    sectors = inv.get("sectors") or "—"
    stages  = inv.get("stages") or "—"
    geo     = inv.get("geo") or inv.get("geo_include") or "—"
    thesis  = inv.get("thesis") or "—"
    check   = ""
    if inv.get("check_min") or inv.get("check_max"):
        rng = f"{inv.get('check_min') or ''} - {inv.get('check_max') or ''}".strip(" -")
        check = f"{rng} {inv.get('check_currency','USD')}".strip()

    def pick(field_name: str) -> Optional[str]:
        for s in snippets:
            cit = s.get("citation") or {}
            if (cit.get("source") == "investor") and (cit.get("field","").lower() == field_name.lower()):
                return s.get("text")
        return None

    if intent == "thesis":
        ref = pick("Thesis") or thesis
        return f"They typically back startups aligned with: {ref}. Focus sectors: {sectors}. Stages: {stages}. Geography: {geo}"
    if intent == "fit":
        if mode == "fit" and (pitch_summary or "").strip():
            return ("Fit overview: Map your pitch to investor focus.\n"
                    f"- Sectors match: {sectors}\n- Stages: {stages}\n- Geography: {geo}\n"
                    "Use the cited investor snippets to justify alignment; avoid areas in Constraints.")
        else:
            return ("This looks like a fit question. On the Profile view I only use investor sources. "
                    "Switch to Fit mode to compare with your pitch.")
    if intent == "sectors":
        ref = pick("Sectors") or sectors
        return f"Preferred sectors/technologies: {ref}."
    if intent == "geo":
        ref = pick("Geography") or geo
        return f"Regional focus: {ref}."
    if intent == "check":
        return f"Typical check size: {check or '—'}. Stage focus: {stages}."
    if intent == "constraints":
        ref = pick("Constraints") or (inv.get("constraints") or "—")
        return f"Notable constraints: {ref}"
    if intent == "diligence":
        return ("Diligence themes likely include: team/market thesis fit, security/compliance posture if relevant, "
                "customer traction and unit economics at target stage, and roadmap vs. check size.")
    if intent == "portfolio":
        return ("Look for adjacent portfolio companies in the same sectors/stages; warm intros via shared angels or "
                "operators work best. (If you sync portfolio data later, I can cite specific names.)")

    # general fallback uses a concise investor overview (not the same sentence every time)
    overview_bits = []
    if thesis and thesis != "—": overview_bits.append(f"Thesis: {thesis}")
    if sectors and sectors != "—": overview_bits.append(f"Sectors: {sectors}")
    if stages and stages != "—": overview_bits.append(f"Stages: {stages}")
    if geo and geo != "—": overview_bits.append(f"Geo: {geo}")
    if check: overview_bits.append(f"Check: {check}")
    if not overview_bits:
        overview_bits.append("No detailed public criteria available.")
    return " | ".join(overview_bits)

@router.post("/qa")
def qa_investor(payload: QAReq, u=Depends(get_current_user), db: Session = Depends(get_session)):
    # Prefer DB; fallback to vector
    inv_row = db.exec(select(Investor).where(Investor.name == payload.name)).first()
    inv = inv_row.dict() if inv_row else _get_investor_object_by_name(payload.name)
    if not inv:
        raise HTTPException(status_code=404, detail="Investor not found")

    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    mode = _choose_mode(payload.mode, question)

    # Build corpora per mode
    inv_chunks = _investor_chunks(inv)                                   # investor-only
    pitch_chunks = _pitch_chunks(payload.pitch_summary or "") if mode == "fit" else []
    combined: List[Tuple[str, Dict[str, Any]]] = inv_chunks + pitch_chunks

    # Rank with fallback (embeddings → keywords). Always return N items.
    N = 3
    ranked = _rank_with_fallback(combined, question, top_k=N)

    # In profile mode, ensure no pitch contamination (guard even though we didn't add)
    if mode == "profile":
        ranked = [r for r in ranked if r["citation"].get("source") == "investor"]
        if len(ranked) < N:
            seen = {r["text"] for r in ranked}
            for text, cite in inv_chunks:
                if text not in seen:
                    ranked.append({"text": text, "score": 0.0, "citation": cite})
                if len(ranked) >= N:
                    break

    # Compose an intent-specific answer
    intent = _classify_intent(question)
    answer = _compose_answer(inv, mode, intent, ranked, payload.pitch_summary or "")

    # persist QA
    db.add(QAResponse(investor_name=inv.get("name") or payload.name, user_id=u.id, question=question, answer=answer))
    db.commit()

    return {
        "answer": answer,
        "snippets": [{"text": r["text"], "score": r["score"]} for r in ranked],
        "citations": ranked,  # includes {source,title,field}
        "mode": mode,
        "intent": intent,
    }