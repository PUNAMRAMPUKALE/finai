# app/routes/recommend.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.matching import find_top_products_for_profile, explain_recommendations

router = APIRouter(prefix="/recommend", tags=["recommend"])

class RecommendReq(BaseModel):
    profile: dict

@router.post("")
def recommend(req: RecommendReq):
    hits = find_top_products_for_profile(req.profile)
    rationale = explain_recommendations(req.profile, hits)
    return {"products": hits, "explanation": rationale}