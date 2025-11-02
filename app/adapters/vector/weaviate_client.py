# app/adapters/vector/weaviate_client.py
from weaviate.classes.config import Property, DataType
from weaviate.classes.init import AdditionalConfig
import weaviate

INVESTOR = "Investor"
_client = None

def get_client():
    global _client
    if _client:
        return _client
    # connect embedded first (no external DB)
    try:
        _client = weaviate.connect_to_embedded(
            additional_config=AdditionalConfig(timeout=(30, 120))
        )
    except Exception:
        # fallback to local docker if you run it
        _client = weaviate.connect_to_local(
            port=8079, grpc_port=50050,
            additional_config=AdditionalConfig(timeout=(30, 120))
        )
    ensure_schema(_client)
    return _client

def ensure_schema(client):
    """
    Canonical schema (structured money fields).
    NOTE: If you previously created the collection with `checkSize` (TEXT),
    you may need to drop/recreate the collection to avoid drift.
    """
    if not client.collections.exists(INVESTOR):
        client.collections.create(
            INVESTOR,
            properties=[
                Property(name="name",           data_type=DataType.TEXT),
                Property(name="firm",           data_type=DataType.TEXT),
                Property(name="sectors",        data_type=DataType.TEXT),
                Property(name="stages",         data_type=DataType.TEXT),
                Property(name="geo",            data_type=DataType.TEXT),
                Property(name="thesis",         data_type=DataType.TEXT),
                Property(name="constraints",    data_type=DataType.TEXT),
                Property(name="profile",        data_type=DataType.TEXT),   # long-form text for RAG
                # Structured money fields (normalized)
                Property(name="check_min",      data_type=DataType.NUMBER),
                Property(name="check_max",      data_type=DataType.NUMBER),
                Property(name="check_currency", data_type=DataType.TEXT),
            ],
        )