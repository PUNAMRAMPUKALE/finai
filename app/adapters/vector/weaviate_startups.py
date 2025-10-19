# app/adapters/vector/weaviate_startups.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from app.adapters.vector.weaviate_client import get_client
from weaviate.classes.config import Property, DataType

# We use a single class for both startup "catalog items" and text chunks.
# If you already created this collection elsewhere, this will just reuse it.
CLASS = "Startup"

def _ensure_schema():
    """
    Make sure the Startup collection exists with the needed properties.
    Safe to call repeatedly; only creates if missing.
    """
    client = get_client()
    if not client.collections.exists(CLASS):
        client.collections.create(
            CLASS,
            properties=[
                Property(name="startupId", data_type=DataType.TEXT),
                Property(name="name", data_type=DataType.TEXT),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),  # for chunks
                Property(name="sector", data_type=DataType.TEXT),
                Property(name="sectors", data_type=DataType.TEXT_ARRAY),
                Property(name="stage", data_type=DataType.TEXT),
                Property(name="stages", data_type=DataType.TEXT_ARRAY),
                Property(name="region", data_type=DataType.TEXT),
                Property(name="geo", data_type=DataType.TEXT),
                Property(name="traction", data_type=DataType.TEXT),
                Property(name="checkSize", data_type=DataType.TEXT),
                Property(name="terms", data_type=DataType.TEXT),
                Property(name="eligibility", data_type=DataType.TEXT),
                Property(name="riskLabel", data_type=DataType.TEXT),
                Property(name="thesis", data_type=DataType.TEXT),
                Property(name="constraints", data_type=DataType.TEXT),
                Property(name="description", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
            ],
        )


def insert_startup(startup: Dict[str, Any], vector: Optional[list] = None) -> str:
    """
    Inserts a single startup "catalog" object (NOT chunks) into Weaviate.
    Returns an opaque object id.
    This satisfies routers that call: from app.adapters.vector.weaviate_startups import insert_startup
    """
    _ensure_schema()
    client = get_client()
    coll = client.collections.get(CLASS)

    # Normalize payload (handle different seed JSON shapes gracefully)
    payload = {
        "startupId": startup.get("id") or startup.get("startupId") or startup.get("name"),
        "name": startup.get("name"),
        "title": startup.get("title") or startup.get("name"),
        "sector": startup.get("sector") or "",
        "sectors": startup.get("sectors") or [],
        "stage": startup.get("stage") or "",
        "stages": startup.get("stages") or [],
        "region": startup.get("region") or "",
        "geo": startup.get("geo") or "",
        "traction": startup.get("traction") or "",
        "checkSize": startup.get("checkSize") or "",
        "terms": startup.get("terms") or "",
        "eligibility": startup.get("eligibility") or "",
        "riskLabel": startup.get("riskLabel") or "",
        "thesis": startup.get("thesis") or "",
        "constraints": startup.get("constraints") or "",
        "description": startup.get("description") or "",
        "source": startup.get("source") or "seed",
        # NOTE: "content" is for text chunks; leave empty here
        "content": "",
    }

    obj = coll.data.insert(payload, vector=vector)
    # v4 client returns an object with id on .uuid or .uuid_… depending on version.
    # Use getattr chain to be safe:
    oid = getattr(obj, "uuid", None) or getattr(obj, "id", None) or ""
    return str(oid)


def insert_startup_chunks(
    startup_id: str,
    title: str,
    chunks: List[str],
    vectors: Optional[List[list]] = None,
    source: str = "startup_pdf",
) -> int:
    """
    Inserts multiple text chunks for one startup PDF (or pitch) into Weaviate.
    - If `vectors` is provided and length matches `chunks`, they are used.
    - Otherwise, rely on Weaviate's vectorizer (if configured) or store without vectors.
    Returns the number of inserted chunks.
    """
    _ensure_schema()
    client = get_client()
    coll = client.collections.get(CLASS)

    use_vecs = bool(vectors) and len(vectors) == len(chunks)
    inserted = 0

    for i, ch in enumerate(chunks):
        vec = vectors[i] if use_vecs else None
        coll.data.insert(
            {
                "startupId": startup_id,
                "title": title,
                "content": ch,
                "source": source,
            },
            vector=vec,
        )
        inserted += 1

    return inserted


def search_similar_in_startups(query_vector: list, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Simple vector search over the Startup class. Returns lightweight rows.
    """
    _ensure_schema()
    coll = get_client().collections.get(CLASS)
    res = coll.query.near_vector(query_vector, limit=limit, return_metadata=["distance"])

    items: List[Dict[str, Any]] = []
    for o in res.objects:
        p = o.properties
        dist = getattr(o.metadata, "distance", None)
        items.append(
            {
                "startupId": p.get("startupId"),
                "name": p.get("name") or p.get("title"),
                "title": p.get("title"),
                "sector": p.get("sector") or ", ".join(p.get("sectors", []) or []),
                "stage": p.get("stage") or ", ".join(p.get("stages", []) or []),
                "region": p.get("region") or p.get("geo", ""),
                "content": p.get("content", ""),
                "distance": dist,
            }
        )
    return items