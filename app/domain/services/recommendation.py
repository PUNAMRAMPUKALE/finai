from typing import Dict, Any, List, Tuple, Literal
from app.ml.embeddings import embed_text
from app.ml.rerank import rerank_pairs
from app.adapters.vector.weaviate_products import search_similar_in_products
from app.adapters.vector.weaviate_startups import search_similar_in_startups
from app.adapters.vector.weaviate_investors import search_similar_in_investors
from app.core.llm import chat_complete

Mode = Literal["profile->products", "startup->investors", "investor->startups"]

def _canon_profile(p: Dict[str, Any]) -> str:
    risk = p.get("riskTolerance") or p.get("risk") or ""
    goal = p.get("investmentGoal") or p.get("goal") or ""
    horizon = p.get("horizonYears") or p.get("horizon_years") or ""
    prefs = ", ".join(p.get("preferences", []))
    cons  = ", ".join(p.get("constraints", []))
    return f"goal={goal}; horizon={horizon} years; risk={risk}; preferences={prefs}; constraints={cons}"

def _canon_item(obj: Dict[str, Any]) -> str:
    fields = ["name","type","sector","sectors","stage","stages","region","geo",
              "terms","fees","eligibility","riskLabel","traction","checkSize","thesis","constraints","description"]
    return " | ".join([str(obj.get(f,"")) for f in fields if obj.get(f)])

def _recall(profile_text: str, mode: Mode, k: int) -> List[Dict[str, Any]]:
    qv = embed_text(profile_text)
    if mode == "startup->investors":
        return search_similar_in_investors(qv, limit=k)
    elif mode == "investor->startups":
        return search_similar_in_startups(qv, limit=k)
    return search_similar_in_products(qv, limit=k)

def _select(profile_text: str, cands: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
    """
    Deterministic selection:
    - Compute semantic similarity via rerank_pairs → [0,1]
    - Convert to % for UI (0..100), clamp + round
    - Sort descending by similarity
    """
    if not cands:
        return []
    pairs = [(profile_text, _canon_item(c)) for c in cands]
    sims = rerank_pairs(pairs)  # [0..1]
    # sort by sim desc
    ranked = sorted(zip(cands, sims), key=lambda x: x[1], reverse=True)[:top_n]
    out: List[Dict[str, Any]] = []
    for item, sim in ranked:
        it = dict(item)
        sim = 0.0 if sim != sim else max(0.0, min(1.0, float(sim)))  # guard NaN, clamp
        it["score"] = sim
        it["score_pct"] = int(round(sim * 100))  # percentage for UI
        out.append(it)
    return out

def _explain(profile_text: str, selected: List[Dict[str, Any]], mode: Mode) -> str:
    bullets = "\n".join([f"- {s.get('name','')} (match {s.get('score_pct',0)}%)" for s in selected])
    instr = {
      "startup->investors": "Explain why each investor fits this startup’s sector, stage, geo, and constraints.",
      "investor->startups": "Explain why each startup fits this fund’s thesis, sectors, stage, geo, and check size.",
      "profile->products":  "Explain product suitability, fees, and risk label for this profile.",
    }[mode]
    prompt = f"""You are a factual fintech assistant. {instr}
Profile: {profile_text}

Candidates:
{bullets}

Return a concise paragraph followed by 3–5 bullet points of rationale. If unknown, say so."""
    try:
        return chat_complete(prompt)
    except Exception:
        lines = [f"- {s.get('name','')} aligns with the profile; match={s.get('score_pct',0)}%" for s in selected]
        return "LLM explanation temporarily unavailable. Top matches were selected via semantic similarity + reranking:\n" + "\n".join(lines)

def recommend(
    profile: Dict[str, Any],
    mode: Mode = "profile->products",
    candidate_k: int = 20,
    top_n: int = 5,
    explain: bool = True,
) -> Dict[str, Any]:
    profile_text = _canon_profile(profile)
    cands = _recall(profile_text, mode, k=candidate_k)
    selected = _select(profile_text, cands, top_n=top_n)
    explanation = _explain(profile_text, selected, mode) if explain else ""
    key = "products" if mode == "profile->products" else "matches"
    return {"mode": mode, key: selected, "explanation": explanation}

def recommend_from_pitch(
    pitch_text: str,
    meta: Dict[str, Any] | None = None,
    candidate_k: int = 20,
    top_n: int = 5,
    explain: bool = True,
) -> Dict[str, Any]:
    meta = meta or {}
    profile_like = {
        "goal": meta.get("goal","fundraising"),
        "risk": meta.get("risk",""),
        "horizon_years": meta.get("horizon", 0),
        "preferences": [meta.get("sector",""), meta.get("stage",""), meta.get("geo",""), meta.get("traction","")],
        "constraints": [],
    }
    profile_text = _canon_profile(profile_like) + f" | pitch: {pitch_text[:1000]}"
    cands = _recall(profile_text, "startup->investors", k=candidate_k)
    selected = _select(profile_text, cands, top_n=top_n)
    explanation = _explain(profile_text, selected, "startup->investors") if explain else ""
    return {"mode": "startup->investors", "matches": selected, "explanation": explanation}