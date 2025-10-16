# app/tools/product_match_llm.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple
import json
import re

from app.core.llm import chat_complete


def llm_select(*, profile_text: str, candidates: List[Dict[str, Any]], top_n: int = 3) -> Dict[str, Any]:
    """
    Ask the LLM to pick the best products for the profile from retrieved candidates.
    Returns a dict with 'products' and 'explanation'.
    NOTE: Embedding/retrieval happens elsewhere; this function only ranks/selects.
    """
    compact = [
        {
            "id": c.get("productId") or c.get("id") or c.get("name"),
            "name": c.get("name"),
            "type": c.get("type"),
            "region": c.get("region"),
            "fees": c.get("fees"),
            "riskLabel": c.get("riskLabel"),
            "terms": (c.get("terms") or "")[:400],
            "description": (c.get("description") or "")[:400],
            "distance": c.get("distance"),
        }
        for c in candidates
    ]

    system = (
        "You are a fiduciary-quality investment assistant. "
        "Choose diversified, suitable products that match the user's risk, goal, horizon, preferences and constraints. "
        "Prefer lower fees when quality is similar. Output STRICT JSON only."
    )

    user = f"""User Profile (text):
{profile_text}

Candidate Products (JSON list):
{json.dumps(compact, ensure_ascii=False, indent=2)}

Task:
Return STRICT JSON with this schema (no extra text):

{{
  "products": [
    {{
      "id": "string",
      "name": "string",
      "why": "1–3 bullet sentences",
      "score": 0-100
    }}
  ],
  "explanation": "Short paragraph explaining the selection and tradeoffs"
}}

Rules:
- Select the top {top_n} products max.
- Be specific about risk/fees/region.
- Do not invent products; only choose from candidates.
- JSON only. No markdown, no commentary.
"""

    raw = chat_complete(system=system, user=user, temperature=0.0, max_tokens=700)

    # Robust JSON extraction
    match = re.search(r"\{.*\}\s*$", raw, flags=re.S)
    text = match.group(0) if match else raw
    try:
        data = json.loads(text)
        products = data.get("products", [])
        explanation = data.get("explanation", "")

        # normalize output
        out = []
        for p in products[:top_n]:
            out.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "why": p.get("why") or "",
                "score": float(p.get("score") or 0),
            })
        return {"products": out, "explanation": explanation}
    except Exception:
        return {"products": [], "explanation": "LLM could not produce valid JSON."}