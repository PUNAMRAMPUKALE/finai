# app/api/v1/routers/ingest.py
from fastapi import APIRouter, HTTPException
from app.api.v1.schemas import IngestDoc, IngestResponse
from app.ml.embeddings import embed_texts
from app.adapters.vector.weaviate_docs import insert_document
from app.core.pdf import pdf_to_text
from app.core.chunking import chunk_text
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("", response_model=IngestResponse)
def ingest(doc: IngestDoc):
    """
    POST /api/v1/ingest
    If you pass a file_path to a 10–20 page PDF, we'll extract text, chunk it,
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

# --- NEW: multipart upload variant ---
@router.post("/file", response_model=IngestResponse)
async def ingest_file(
    title: str = Form(...),
    source: str = Form("upload"),
    file: UploadFile = File(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF uploads are supported.")
    # Read bytes -> write temp file -> reuse pdf_to_text (or directly parse bytes if you prefer)
    data = await file.read()
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        text = pdf_to_text(tmp_path)
    finally:
        os.unlink(tmp_path)
    chunks = chunk_text(text)
    vectors = embed_texts(chunks)
    for ch, vec in zip(chunks, vectors):
        insert_document(title=title, content=ch, source=source, vector=vec)
    return IngestResponse(inserted=len(chunks))