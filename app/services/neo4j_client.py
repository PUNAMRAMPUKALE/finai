# app/services/neo4j_client.py
# Purpose: single Neo4j driver used across the app.
from neo4j import GraphDatabase
from app.config import settings

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
    with get_driver().session() as session:
        return list(session.run(query, params or {}))
