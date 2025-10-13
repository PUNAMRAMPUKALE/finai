# app/services/matching.py
from typing import List, Dict
from app.services.embeddings import embed_text, embed_texts
from app.services.weaviate_db import search_similar_in_products
from app.services.openai_client import chat_complete

def find_top_products_for_profile(profile: dict, top_k: int = 5) -> List[Dict]:
    """
    Convert the user's profile to a single descriptive sentence and embed it,
    then search closest products by meaning.
    """
    text = (
        f"goal {profile['goal']}; horizon {profile['horizon_years']} years; "
        f"risk {profile['risk']}; preferences {', '.join(profile.get('preferences', []))}; "
        f"constraints {', '.join(profile.get('constraints', []))}"
    )
    vec = embed_text(text)
    return search_similar_in_products(vec, limit=top_k)

def explain_recommendations(profile: dict, products: List[Dict]) -> str:
    """
    Ask OpenAI to summarize why these products fit this profile, referencing items [1], [2], ...
    """
    lines = []
    for i, p in enumerate(products, 1):
        lines.append(f"[{i}] {p['name']} — fees: {p.get('fees','')}; region: {p.get('region','')}; risk: {p.get('riskLabel','')}")
    catalog = "\n".join(lines)
    prompt = f"""User profile: goal={profile['goal']}, horizon={profile['horizon_years']}y, risk={profile['risk']},
preferences={profile.get('preferences', [])}, constraints={profile.get('constraints', [])}.

Products:
{catalog}

Rank them and give 2-3 short reasons each. Reference by [1], [2], etc.
"""
    return chat_complete(prompt)
