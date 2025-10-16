# app/domain/services/rag.py
from typing import List, Tuple
from app.ml.embeddings import embed_text
from app.adapters.vector.weaviate_docs import search_similar_in_docs
from app.core.llm import chat_complete

def answer_with_rag(question: str, top_k: int = 5) -> Tuple[str, List[str]]:
    """
    RAG flow:
    1) embed question
    2) retrieve top-K doc chunks
    3) build numbered context
    4) ask LLM to answer using ONLY the context, with [1], [2] citations
    """
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

    system = "You are a fintech analyst. Only use the provided context; cite with [1], [2], etc."
    user = f"""Question: {question}

Context:
{context}

Write a concise answer with numbered citations. If unknown, say so.
"""

    answer = chat_complete(system=system, user=user, temperature=0.2, max_tokens=700)
    return answer, sources