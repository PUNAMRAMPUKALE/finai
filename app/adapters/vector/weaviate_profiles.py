from .weaviate_client import get_client, USER

def upsert_user_profile(profile: dict, vector: list | None):
    coll = get_client().collections.get(USER)
    coll.data.insert({
        "profileId": profile["profile_id"],
        "goal": profile["goal"],
        "risk": profile["risk"],
        "preferences": profile.get("preferences", []),
        "constraints": profile.get("constraints", []),
    }, vector=vector)