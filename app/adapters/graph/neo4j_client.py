from neo4j import GraphDatabase
from app.config import settings
from app.core.logging import get_logger

log = get_logger("neo4j")
_driver = None

def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver

def run_cypher(query: str, params: dict | None = None):
    try:
        with get_driver().session() as session:
            return list(session.run(query, params or {}))
    except Exception:
        # Log a safe snippet + param keys (not values) to avoid leaking secrets
        log.exception("neo4j_cypher_failed", extra={"snippet": query[:120], "params_keys": list((params or {}).keys())})
        raise