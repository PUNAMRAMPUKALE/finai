# app/routes/recommend.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.matching import find_top_products_for_profile, explain_recommendations

router = APIRouter(prefix="/recommend", tags=["recommend"])


class RecommendReq(BaseModel):
    profile: dict


@router.post("")
def recommend(req: RecommendReq):
    """
    POST /recommend
    Uses the new LLM-based product matching system.
    - Embeds the profile.
    - Retrieves candidate products from Weaviate.
    - LLM selects and ranks the top matches.
    """
    profile = req.profile

    # normalize key names for backward compatibility
    profile.setdefault("riskTolerance", profile.get("risk"))
    profile.setdefault("investmentGoal", profile.get("goal"))
    profile.setdefault("horizonYears", profile.get("horizon_years"))

    try:
        hits = find_top_products_for_profile(profile)
        rationale = explain_recommendations(profile, hits)
        return {
            "status": "ok",
            "count": len(hits),
            "products": hits,
            "explanation": rationale,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {e}")