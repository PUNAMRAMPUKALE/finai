# app/adapters/vector/weaviate_client.py
from __future__ import annotations

import os
import weaviate
from weaviate.classes.init import AdditionalConfig
from weaviate.classes.config import Property, DataType, Configure

INVESTOR = "Investor"
_client = None


def get_client():
    """
    Returns a singleton Weaviate client.

    Strategy:
    1) If WEAVIATE_EMBEDDED=1 -> embedded Weaviate (no docker needed)
    2) Else -> connect to a local Weaviate you run yourself (docker / remote)
    """
    global _client
    if _client:
        return _client

    timeout_cfg = AdditionalConfig(timeout=(30, 120))
    use_embedded = os.getenv("WEAVIATE_EMBEDDED", "1") == "1"

    if use_embedded:
        # Embedded Weaviate (stores data locally)
        # NOTE: Embedded will download binaries on first run.
        _client = weaviate.connect_to_embedded(additional_config=timeout_cfg)
    else:
        # Local Weaviate (YOU must run it)
        # These ports should match your Weaviate container/service
        _client = weaviate.connect_to_local(
            port=int(os.getenv("WEAVIATE_HTTP_PORT", "8080")),
            grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
            additional_config=timeout_cfg,
        )

    ensure_schema(_client)
    return _client


def ensure_schema(client):
    """
    Canonical schema (structured money fields).

    IMPORTANT:
    - We set vectorizer=none because YOU are providing vectors (embed_text) yourself.
    - If the collection already exists with different property types (schema drift),
      drop & recreate it (see reset function below).
    """
    if client.collections.exists(INVESTOR):
        return

    client.collections.create(
        name=INVESTOR,
        properties=[
            Property(name="name",           data_type=DataType.TEXT),
            Property(name="firm",           data_type=DataType.TEXT),
            Property(name="sectors",        data_type=DataType.TEXT),
            Property(name="stages",         data_type=DataType.TEXT),
            Property(name="geo",            data_type=DataType.TEXT),
            Property(name="thesis",         data_type=DataType.TEXT),
            Property(name="constraints",    data_type=DataType.TEXT),
            Property(name="profile",        data_type=DataType.TEXT),

            Property(name="check_min",      data_type=DataType.NUMBER),
            Property(name="check_max",      data_type=DataType.NUMBER),
            Property(name="check_currency", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.hnsw(),
    )


def reset_collection(client):
    """
    Use ONLY if you have schema drift (old types like checkSize TEXT).
    """
    if client.collections.exists(INVESTOR):
        client.collections.delete(INVESTOR)
    ensure_schema(client)
