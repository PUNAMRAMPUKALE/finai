from typing import List, Dict, Any, Tuple
from app.ml.embeddings import embed_texts, embed_text
import math

def _cos_sim(a: List[float], b: List[float]) -> float:
    return sum(x*y for x,y in zip(a,b))

def split_paragraphs(text: str, max_len: int = 600) -> List[str]:
    if not text:
        return []
    raw = [p.strip() for p in text.replace("\r","").split("\n") if p.strip()]
    out: List[str] = []
    buf = ""
    for p in raw:
        if len(buf) + 1 + len(p) < max_len:
            buf = (buf + " " + p).strip()
        else:
            if buf: out.append(buf)
            buf = p
    if buf: out.append(buf)
    return out

def retrieve(passages: List[str], query: str, top_k: int = 4) -> List[Tuple[str, float]]:
    if not passages:
        return []
    qv = embed_text(query)
    p_vecs = embed_texts(passages)
    scored = [(p, _cos_sim(qv, pv)) for p, pv in zip(passages, p_vecs)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]

def agents_analysis(investor: Dict[str, Any], pitch_summary: str) -> Dict[str, Any]:
    """Three tiny ‘agents’ emitting structured insights (rule+retrieval)."""
    inv_text = " | ".join([
        investor.get("name",""),
        investor.get("sectors",""),
        investor.get("stages",""),
        investor.get("geo",""),
        investor.get("checkSize",""),
        investor.get("thesis",""),
        investor.get("constraints",""),
        investor.get("profile",""),
    ]).strip()

    # Retrieval context
    passages = split_paragraphs(inv_text, max_len=500) or [inv_text]
    why_query = f"Why is this investor a fit for startup with: {pitch_summary}"
    top = retrieve(passages, why_query, top_k=4)

    # --- Agents ---
    def strategy_agent():
        bullets = []
        if any(k.lower() in inv_text.lower() for k in ["ai","robotics","ml"]):
            bullets.append("Focus on AI/Robotics aligns with your product direction.")
        if any(k.lower() in inv_text.lower() for k in ["fintech","saas","devtools"]):
            bullets.append("FinTech/SaaS/DevTools focus overlaps with your category.")
        if "network effects" in inv_text.lower():
            bullets.append("Preference for network effects—highlight flywheel metrics.")
        if not bullets: bullets.append("Overall sector & thesis appear compatible.")
        return {"agent":"StrategyAgent","summary":"Sector & thesis alignment","bullets":bullets}

    def risk_agent():
        bullets = []
        if "no crypto" in inv_text.lower():
            bullets.append("Constraint: avoids crypto—avoid crypto-centric narrative.")
        if "hardware" in inv_text.lower():
            bullets.append("Constraint on heavy hardware—emphasize software margins.")
        if "north america only" in inv_text.lower():
            bullets.append("Geo focus: North America—clarify your GTM regions.")
        if not bullets: bullets.append("No major red flags detected from stated constraints.")
        return {"agent":"RiskAgent","summary":"Constraints & risk checks","bullets":bullets}

    def fit_agent(score_hint: int):
        bullets = [
            f"Current match score suggests positive interest vector (≈{score_hint}%).",
            "Map traction to their check size and preferred stages.",
            "Tie your KPIs to their thesis keywords (use retrieved snippets).",
        ]
        return {"agent":"FitExplainer","summary":"How to pitch this investor","bullets":bullets}

    score_hint = 0
    # heuristic score from retrieval sims (0..100)
    if top:
        # normalize cosine (approx since vectors are normalized)
        sims = [s for _, s in top]
        score_hint = int(round(max(0.0, min(1.0, (sum(sims)/max(1,len(sims))+1)/2))*100))

    return {
        "context_snippets": [{"text": p, "score": round(s,4)} for p,s in top],
        "agents": [strategy_agent(), risk_agent(), fit_agent(score_hint)],
        "score_hint": score_hint,
    }

def rag_qa(investor: Dict[str, Any], pitch_summary: str, question: str) -> Dict[str, Any]:
    ctx = " ".join(filter(None, [
        investor.get("thesis",""),
        investor.get("sectors",""),
        investor.get("stages",""),
        investor.get("geo",""),
        investor.get("constraints",""),
        investor.get("profile",""),
        pitch_summary or "",
    ]))
    chunks = split_paragraphs(ctx, 500) or [ctx]
    top = retrieve(chunks, question, top_k=3)
    answer = (
        "Based on the investor’s thesis/constraints and your pitch summary, here are the most relevant notes:\n- "
        + "\n- ".join(p for p,_ in top)
        + "\n\nRecommendation: tailor your message to the retrieved points above."
    )
    return {"answer": answer, "snippets": [{"text": p, "score": s} for p,s in top]}