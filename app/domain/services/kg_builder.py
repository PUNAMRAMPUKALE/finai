# app/domain/services/kg_builder.py
import re
from typing import List, Tuple, Iterable, Optional
from app.adapters.graph.neo4j_client import run_cypher
from app.adapters.vector.weaviate_client import get_client

# Triple layout: (subject, relation, object, source)
Triple = Tuple[str, str, str, str]

def _sanitize_rel(rel: str) -> str:
    rel = rel.strip()
    rel = re.sub(r"[^A-Za-z0-9]+", "_", rel)
    rel = rel.strip("_").upper()
    return rel or "RELATED_TO"

def upsert_triples(triples: List[Triple]) -> int:
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
    client = get_client()
    coll = client.collections.get("Document")
    yielded = 0
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
    triples: List[Triple] = []
    triples.append((title, "HAS_SOURCE", source, source))
    for pct in re.findall(r"\b\d+(?:\.\d+)?%\b", content)[:5]:
        triples.append((title, "MENTIONS", pct, source))
    words = re.findall(r"\b[A-Z][A-Za-z0-9\-]{2,}\b", content)
    for w in list(dict.fromkeys(words))[:5]:
        triples.append((title, "MENTIONS", w, source))
    return triples

def build_graph_from_docs(max_docs: Optional[int] = None) -> int:
    total = 0
    batch: List[Triple] = []
    for doc in _iter_docs(limit=max_docs):
        t = _extract_triples(doc["title"], doc["content"], doc["source"])
        batch.extend(t)
        if len(batch) >= 200:
            total += upsert_triples(batch)
            batch = []
    if batch:
        total += upsert_triples(batch)
    return total