# app/ml/rag_utils.py
from __future__ import annotations

from typing import List, Dict, Any, Tuple
from app.ml.embeddings import embed_texts, embed_text

# ----------------------------
# Similarity & basic utilities
# ----------------------------

def _cos_sim(a: List[float], b: List[float]) -> float:
    """
    Cosine similarity for *normalized* vectors.
    Because embed_text(s) returns unit vectors, dot == cosine in [-1, 1].
    If vectors are different length (shouldn't happen), zip truncates safely.
    """
    return sum(x * y for x, y in zip(a, b))


def split_paragraphs(text: str, max_len: int = 600) -> List[str]:
    """
    Greedy paragraph joiner:
    - Splits input on newlines
    - Re-wraps into chunks up to ~max_len chars (soft limit)
    - Preserves paragraph boundaries as much as possible
    """
    if not text:
        return []
    raw = [p.strip() for p in text.replace("\r", "").split("\n") if p.strip()]
    out: List[str] = []
    buf = ""
    for p in raw:
        if len(buf) + (1 if buf else 0) + len(p) <= max_len:
            buf = (buf + " " + p).strip()
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out


# ----------------------------
# Retrieval
# ----------------------------

def retrieve(passages: List[str], query: str, top_k: int = 4) -> List[Tuple[str, float]]:
    """
    Standard dense retrieval:
    - Embed query & passages (L2-normalized)
    - Score with cosine (dot)
    - Return top_k (text, score) sorted desc by score
    """
    if not passages or not query:
        return []
    qv = embed_text(query)
    p_vecs = embed_texts(passages)
    scored = [(p, _cos_sim(qv, pv)) for p, pv in zip(passages, p_vecs)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:max(1, top_k)]


# ----------------------------
# Formatting helpers
# ----------------------------

def _fmt_money(inv: Dict[str, Any]) -> str:
    mn = inv.get("check_min")
    mx = inv.get("check_max")
    cur = inv.get("check_currency") or "USD"
    if mn is None and mx is None:
        return ""
    rng = f"{mn or ''} - {mx or ''}".strip(" -")
    return f"{rng} {cur}".strip()


# ----------------------------
# Agentic analysis (3 tiny agents)
# ----------------------------

def agents_analysis(investor: Dict[str, Any], pitch_summary: str) -> Dict[str, Any]:
    """
    Agentic-style structured analysis over investor metadata + pitch summary.
    - Builds retrieval context from the investor profile fields
    - Uses dense retrieval to ground simple rule-based agents
    - Emits context snippets, agent bullets, and a percentage-like score hint
    """
    money = _fmt_money(investor)
    inv_text = " | ".join(
        filter(
            None,
            [
                investor.get("name", ""),
                investor.get("sectors", ""),
                investor.get("stages", ""),
                investor.get("geo", ""),
                money,
                investor.get("thesis", ""),
                investor.get("constraints", ""),
                investor.get("profile", ""),
            ],
        )
    )

    # Retrieval context
    passages = split_paragraphs(inv_text, max_len=500) or [inv_text]
    why_query = f"Why is this investor a fit for startup with: {pitch_summary}"
    top = retrieve(passages, why_query, top_k=4)

    # --- Agents (simple, explainable rules) ---
    inv_lower = inv_text.lower()

    def strategy_agent():
        bullets: List[str] = []
        if any(k in inv_lower for k in ["ai", "robotics", "ml"]):
            bullets.append("Focus on AI/Robotics aligns with your product direction.")
        if any(k in inv_lower for k in ["fintech", "saas", "devtools"]):
            bullets.append("FinTech/SaaS/DevTools focus overlaps with your category.")
        if "network effects" in inv_lower:
            bullets.append("Preference for network effects—highlight flywheel metrics.")
        if not bullets:
            bullets.append("Overall sector & thesis appear compatible.")
        return {"agent": "StrategyAgent", "summary": "Sector & thesis alignment", "bullets": bullets}

    def risk_agent():
        bullets: List[str] = []
        if "no crypto" in inv_lower:
            bullets.append("Constraint: avoids crypto—avoid crypto-centric narrative.")
        if "hardware" in inv_lower:
            bullets.append("Constraint on heavy hardware—emphasize software margins.")
        if "north america only" in inv_lower:
            bullets.append("Geo focus: North America—clarify your GTM regions.")
        if not bullets:
            bullets.append("No major red flags detected from stated constraints.")
        return {"agent": "RiskAgent", "summary": "Constraints & risk checks", "bullets": bullets}

    def fit_agent(score_hint: int):
        bullets = [
            f"Current match score suggests positive interest vector (≈{score_hint}%).",
            "Map traction to their check size and preferred stages.",
            "Tie your KPIs to their thesis keywords (use retrieved snippets).",
        ]
        return {"agent": "FitExplainer", "summary": "How to pitch this investor", "bullets": bullets}

    # Convert cosine ([-1,1]) to a rough 0–100% hint using the mean similarity
    score_hint = 0
    if top:
        sims = [s for _, s in top]
        # Normalize mean cosine to [0,100]
        score_hint = int(round(max(0.0, min(1.0, (sum(sims) / max(1, len(sims)) + 1) / 2)) * 100))

    return {
        "context_snippets": [{"text": p, "score": round(s, 4)} for p, s in top],
        "agents": [strategy_agent(), risk_agent(), fit_agent(score_hint)],
        "score_hint": score_hint,
    }


# ----------------------------
# RAG QA (context retrieval + templated answer)
# ----------------------------

def rag_qa(investor: Dict[str, Any], pitch_summary: str, question: str) -> Dict[str, Any]:
    """
    Build a compact context from investor profile + pitch summary,
    retrieve top chunks against the user question, and return a templated answer.
    (Hook your LLM here if needed; this is a pure-RAG skeleton output.)
    """
    ctx = " ".join(
        filter(
            None,
            [
                investor.get("thesis", ""),
                investor.get("sectors", ""),
                investor.get("stages", ""),
                investor.get("geo", ""),
                investor.get("constraints", ""),
                investor.get("profile", ""),
                _fmt_money(investor),
                pitch_summary or "",
            ],
        )
    )

    chunks = split_paragraphs(ctx, 500) or [ctx]
    top = retrieve(chunks, question, top_k=3)

    answer = (
        "Based on the investor’s thesis/constraints and your pitch summary, here are the most relevant notes:\n- "
        + "\n- ".join(p for p, _ in top)
        + "\n\nRecommendation: tailor your message to the retrieved points above."
    )

    return {
        "answer": answer,
        "snippets": [{"text": p, "score": round(s, 4)} for p, s in top],
    }