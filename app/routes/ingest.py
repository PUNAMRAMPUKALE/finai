# app/routes/ingest.py
from fastapi import APIRouter, HTTPException
from app.schemas import IngestDoc, IngestResponse
from app.services.embeddings import embed_texts
from app.services.weaviate_db import insert_document
from app.utils.pdf_loader import pdf_to_text
from app.utils.text_chunker import chunk_text

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("", response_model=IngestResponse)
def ingest(doc: IngestDoc):
    """
    POST /ingest
    - If you pass a file_path to a 10–20 page PDF, we'll extract text, chunk it,
      create vectors, and store them for search.
    """
    if not doc.text and not doc.file_path:
        raise HTTPException(400, "Provide either 'text' or 'file_path' to a PDF.")
    text = doc.text or pdf_to_text(doc.file_path)
    chunks = chunk_text(text)
    vectors = embed_texts(chunks)
    for ch, vec in zip(chunks, vectors):
        insert_document(title=doc.title, content=ch, source=doc.source or doc.title, vector=vec)
    return IngestResponse(inserted=len(chunks))
