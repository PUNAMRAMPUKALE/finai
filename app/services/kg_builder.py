# app/services/kg_builder.py
import re
from typing import List, Tuple, Iterable, Optional
from app.services.neo4j_client import run_cypher
from app.services.weaviate_db import get_client

# Triple layout: (subject, relation, object, source)
Triple = Tuple[str, str, str, str]

def _sanitize_rel(rel: str) -> str:
    """Neo4j relationship types must be [A-Za-z0-9_]; convert others to underscores."""
    rel = rel.strip()
    rel = re.sub(r"[^A-Za-z0-9]+", "_", rel)  # non-alnum -> underscore
    rel = rel.strip("_").upper()
    return rel or "RELATED_TO"

def upsert_triples(triples: List[Triple]) -> int:
    """
    Insert triples into Neo4j using fixed :Entity labels and a safe rel type.
    Uses elementId() (supported) instead of deprecated id().
    """
    count = 0
    for subject, relation, obj, source in triples:
        rel_type = _sanitize_rel(relation)
        cypher = f"""
        MERGE (s:Entity {{name: $subject}})
        MERGE (o:Entity {{name: $object}})
        MERGE (s)-[r:{rel_type} {{source: $source}}]->(o)
        RETURN elementId(r) AS rel_id
        """
        run_cypher(cypher, {"subject": subject, "object": obj, "source": source})
        count += 1
    return count

def _iter_docs(limit: Optional[int] = None) -> Iterable[dict]:
    """
    Yield Document objects from Weaviate with fields: title, content, source.

    Uses the v4 client collection iterator to avoid manual paging bugs.
    This will stream all objects; 'limit' stops early if provided.
    """
    client = get_client()
    coll = client.collections.get("Document")
    yielded = 0

    # The iterator yields objects with `.properties` populated
    for o in coll.iterator():
        data = o.properties or {}
        yield {
            "title": data.get("title", "Untitled"),
            "content": data.get("content", ""),
            "source": data.get("source", "unknown"),
        }
        yielded += 1
        if limit is not None and yielded >= limit:
            break

def _extract_triples(title: str, content: str, source: str) -> List[Triple]:
    """
    SUPER-simple extractor to get you going:
    - (title) -HAS_SOURCE-> (source)
    - (title) -MENTIONS-> (each % number like 0.19%)
    - (title) -MENTIONS-> (handful of capitalized tokens)

    This is intentionally naive; you can later swap in an LLM-based extractor.
    """
    triples: List[Triple] = []

    # Always connect doc to its source
    triples.append((title, "HAS_SOURCE", source, source))

    # Percentages like 0.19% or 2%
    for pct in re.findall(r"\b\d+(?:\.\d+)?%\b", content)[:5]:
        triples.append((title, "MENTIONS", pct, source))

    # Capitalized terms (rough keywords)
    words = re.findall(r"\b[A-Z][A-Za-z0-9\-]{2,}\b", content)
    for w in list(dict.fromkeys(words))[:5]:  # de-dupe, keep top 5
        triples.append((title, "MENTIONS", w, source))

    return triples

def build_graph_from_docs(max_docs: Optional[int] = None) -> int:
    """
    Build KG by scanning docs in Weaviate and inserting extracted triples.
    Always returns an integer count (0 if no docs/triples).
    """
    total = 0
    batch: List[Triple] = []

    for doc in _iter_docs(limit=max_docs):
        t = _extract_triples(doc["title"], doc["content"], doc["source"])
        batch.extend(t)

        # Flush every ~200 triples for memory friendliness
        if len(batch) >= 200:
            total += upsert_triples(batch)
            batch = []

    if batch:
        total += upsert_triples(batch)

    return total
