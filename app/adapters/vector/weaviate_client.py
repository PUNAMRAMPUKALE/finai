# app/services/weaviate_db.py
from app.config import settings
from app.utils.logging import get_logger
import weaviate
from weaviate.classes.config import Property, DataType
from weaviate.classes.init import AdditionalConfig
import weaviate

log = get_logger("weaviate")

# Global client (shared)
_client = None

# We define 3 "classes" (think: tables)
DOCS = "Document"     # chunks from your PDFs
PROD = "Product"      # product catalog items (for matching)
USER = "UserProfile"  # user profiles for matching context

def _ensure_collections(client):
    """
    Ensure the three collections exist. Works with weaviate-client 4.9.x
    where list_all() returns list[str].
    """
    def ensure_coll(name: str, props: list):
        if not client.collections.exists(name):
            client.collections.create(name, properties=props)

    ensure_coll(DOCS, [
        Property(name="title", data_type=DataType.TEXT),
        Property(name="content", data_type=DataType.TEXT),
        Property(name="source", data_type=DataType.TEXT),
    ])
    ensure_coll(PROD, [
        Property(name="productId", data_type=DataType.TEXT),
        Property(name="name", data_type=DataType.TEXT),
        Property(name="type", data_type=DataType.TEXT),
        Property(name="terms", data_type=DataType.TEXT),
        Property(name="fees", data_type=DataType.TEXT),
        Property(name="eligibility", data_type=DataType.TEXT),
        Property(name="region", data_type=DataType.TEXT),
        Property(name="riskLabel", data_type=DataType.TEXT),
        Property(name="description", data_type=DataType.TEXT),
    ])
    ensure_coll(USER, [
        Property(name="profileId", data_type=DataType.TEXT),
        Property(name="goal", data_type=DataType.TEXT),
        Property(name="risk", data_type=DataType.TEXT),
        Property(name="preferences", data_type=DataType.TEXT_ARRAY),
        Property(name="constraints", data_type=DataType.TEXT_ARRAY),
    ])



def get_client():
    global _client
    if _client:
        return _client

    try:
        log.info("Starting Weaviate embedded...")
        _client = weaviate.connect_to_embedded(
            additional_config=AdditionalConfig(timeout=(30, 120)),
        )
    except Exception as e:
        if "already listening on ports" in str(e):
            log.info("Embedded already running; connecting to local Weaviate on :8079 / :50050")
            _client = weaviate.connect_to_local(
                port=8079,
                grpc_port=50050,
                additional_config=AdditionalConfig(timeout=(30, 120)),
            )
        else:
            raise

    _ensure_collections(_client)
    return _client


# ---------- Document helpers (PDF chunks) ----------

def insert_document(title: str, content: str, source: str, vector: list | None):
    coll = get_client().collections.get(DOCS)
    coll.data.insert({"title": title, "content": content, "source": source}, vector=vector)

def search_similar_in_docs(query_vector: list, limit: int = 5):
    coll = get_client().collections.get(DOCS)
    res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance"])
    items = []
    for o in res.objects:
        props = o.properties
        # v4.9: metadata is an object, not a dict
        dist = getattr(o.metadata, "distance", None)
        items.append({
            "title": props.get("title"),
            "content": props.get("content"),
            "source": props.get("source"),
            "distance": dist,
        })
    return items

# ---------- Product helpers (catalog) ----------

def insert_product(prod: dict, vector: list | None):
    """
    Stores a product with its vector so we can match profiles to products.
    """
    coll = get_client().collections.get(PROD)
    payload = {
        "productId": prod.get("id") or prod.get("productId") or prod.get("name"),
        "name": prod.get("name", ""),
        "type": prod.get("type", ""),
        "terms": (prod.get("terms", "") + " " + prod.get("description", "")).strip(),
        "fees": prod.get("fees", ""),
        "eligibility": prod.get("eligibility", ""),
        "region": prod.get("region", ""),
        "riskLabel": prod.get("riskLabel", ""),
        "description": prod.get("description", ""),
    }
    coll.data.insert(payload, vector=vector)

def search_similar_in_products(query_vector: list, limit: int = 5):
    coll = get_client().collections.get(PROD)
    res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance"])
    items = []
    for o in res.objects:
        p = o.properties
        dist = getattr(o.metadata, "distance", None)
        items.append({
            "productId": p.get("productId"),
            "name": p.get("name"),
            "type": p.get("type"),
            "terms": p.get("terms"),
            "fees": p.get("fees"),
            "eligibility": p.get("eligibility"),
            "region": p.get("region"),
            "riskLabel": p.get("riskLabel"),
            "description": p.get("description"),
            "distance": dist,
        })
    return items

# ---------- User profile helpers ----------

def upsert_user_profile(profile: dict, vector: list | None):
    """
    Stores a user profile vector so we can find similar products.
    """
    coll = get_client().collections.get(USER)
    coll.data.insert({
        "profileId": profile["profile_id"],
        "goal": profile["goal"],
        "risk": profile["risk"],
        "preferences": profile.get("preferences", []),
        "constraints": profile.get("constraints", []),
    }, vector=vector)

def list_all_docs(limit: int = 1000):
    """
    Returns all Document objects' lightweight info for KG building.
    """
    coll = get_client().collections.get(DOCS)
    # v4.9: fetch_objects is the simplest way to iterate
    res = coll.query.fetch_objects(limit=limit)
    out = []
    for o in res.objects:
        p = o.properties
        out.append({
            "title": p.get("title"),
            "content": p.get("content"),
            "source": p.get("source"),
        })
    return out    
