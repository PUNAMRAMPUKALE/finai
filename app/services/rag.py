# app/services/rag.py
from typing import List
from app.services.embeddings import embed_text
from app.services.weaviate_db import search_similar_in_docs
from app.services.openai_client import chat_complete

def answer_with_rag(question: str, top_k: int = 5) -> tuple[str, List[str]]:
    """
    1) Turn the question into a vector.
    2) Find the most similar PDF chunks.
    3) Ask OpenAI to answer only using those chunks, with [1], [2] citations.
    """
    q_vec = embed_text(question)
    hits = search_similar_in_docs(q_vec, limit=top_k)

    # Build a context block the LLM can read and cite
    blocks, sources = [], []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[{i}] Title: {h['title']}\nSource: {h['source']}\n{h['content'][:1200]}")
        sources.append(f"{i}:{h['source'] or h['title']}")
    context = "\n\n".join(blocks)

    prompt = f"""You are a fintech analyst. Only use the context below to answer. Cite with [1], [2], etc.
Question: {question}

Context:
{context}

Write a concise answer with numbered citations.
"""
    answer = chat_complete(prompt)
    return answer, sources
