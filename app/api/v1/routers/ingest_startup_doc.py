from fastapi import APIRouter, UploadFile, Form
from app.domain.services.rag import ingest_startup_pdf

router = APIRouter(prefix="/api/v1/ingest/startup", tags=["ingest"])

@router.post("/pdf")
async def ingest_startup_pdf_endpoint(file: UploadFile, title: str = Form("Konstellation"), source: str = Form("startup_pitch")):
    text, meta = await ingest_startup_pdf(file, title, source)
    return {"status": "ok", "title": title, "chunks": len(text), "meta": meta}