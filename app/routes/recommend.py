# app/routes/recommend.py
from fastapi import APIRouter
from app.schemas import RecommendRequest, RecommendResponse, RecommendationItem
from app.services.matching import find_top_products_for_profile, explain_recommendations

router = APIRouter(prefix="/recommend", tags=["recommend"])

@router.post("", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    """
    POST /recommend
    Returns top products matched to a user's profile, plus an explanation.
    """
    hits = find_top_products_for_profile(req.profile.model_dump(), top_k=req.top_k)
    rationale = explain_recommendations(req.profile.model_dump(), hits)

    items = []
    for h in hits:
        score = max(0.0, 1.0 - float(h.get("distance", 0.5)))  # turn distance into a 0..1 score
        items.append(RecommendationItem(
            productId=h["name"].replace(" ", "_"),
            score=round(score, 3),
            rationale=[rationale],  # concise combined reasoning
            key_stats={"fees": h.get("fees",""), "region": h.get("region",""), "riskLabel": h.get("riskLabel","")},
            sources=[h.get("terms","")]
        ))
    return RecommendResponse(items=items)
