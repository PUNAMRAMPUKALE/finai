from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.v1.deps import get_recommend

# ✅ add the prefix so the route is /api/v1/recommend
router = APIRouter(prefix="/recommend", tags=["recommend"])

class RecommendReq(BaseModel):
    profile: dict

@router.post("")
def recommend(req: RecommendReq, recommend_usecase = Depends(get_recommend)):
    # normalize keys for compatibility
    p = req.profile
    p.setdefault("riskTolerance", p.get("risk"))
    p.setdefault("investmentGoal", p.get("goal"))
    p.setdefault("horizonYears", p.get("horizon_years"))

    try:
        result = recommend_usecase(p)  # calls app/domain/services/recommendation.py
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(500, f"Recommendation error: {e}")