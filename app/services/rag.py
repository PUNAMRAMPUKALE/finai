# app/services/rag.py  (unchanged)
from typing import List, Tuple
from app.services.embeddings import embed_text
from app.services.weaviate_db import search_similar_in_docs
from app.services.openai_client import chat_complete

def answer_with_rag(question: str, top_k: int = 5) -> Tuple[str, List[str]]:
    q_vec = embed_text(question)
    hits = search_similar_in_docs(q_vec, limit=top_k)

    if not hits:
        return "I couldn't find relevant evidence in the knowledge base.", []

    blocks, sources = [], []
    for i, h in enumerate(hits, 1):
        snippet = (h.get("content") or "")[:1200]
        title = h.get("title") or "Doc"
        src = h.get("source") or title
        blocks.append(f"[{i}] Title: {title}\nSource: {src}\n{snippet}")
        sources.append(f"{i}:{src}")

    context = "\n\n".join(blocks)
    prompt = f"""You are a fintech analyst. Only use the context below to answer and cite with [1], [2], etc.

Question: {question}

Context:
{context}

Write a concise answer with numbered citations. If unknown, say so.
"""
    answer = chat_complete(prompt)
    return answer, sources