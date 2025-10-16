from weaviate.classes.config import Property, DataType
from weaviate.classes.init import AdditionalConfig
import weaviate

DOCS = "Document"
PROD = "Product"
USER = "UserProfile"
_client = None

def get_client():
    global _client
    if _client:
        return _client
    try:
        _client = weaviate.connect_to_embedded(additional_config=AdditionalConfig(timeout=(30,120)))
    except Exception:
        _client = weaviate.connect_to_local(port=8079, grpc_port=50050, additional_config=AdditionalConfig(timeout=(30,120)))
    ensure_schema(_client)
    return _client

def ensure_schema(client):
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