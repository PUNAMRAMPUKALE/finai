# app/routes/profiles.py
from fastapi import APIRouter
from app.api.v1.schemas import Profile
from app.ml.embeddings import embed_text
from app.adapters.vector.weaviate_profiles import upsert_user_profile


router = APIRouter(prefix="/profiles", tags=["profiles"])

@router.post("")
def upsert_profile(profile: Profile):
    """
    POST /profiles
    Creates or updates a profile and stores a vector representation for matching.
    """
    text = (
        f"goal {profile.goal}; horizon {profile.horizon_years} years; "
        f"risk {profile.risk}; preferences {', '.join(profile.preferences)}; "
        f"constraints {', '.join(profile.constraints)}"
    )
    vec = embed_text(text)
    upsert_user_profile(profile.model_dump(), vec)
    return {"status": "ok", "profile_id": profile.profile_id}
