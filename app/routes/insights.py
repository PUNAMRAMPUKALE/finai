# app/routes/insights.py
from fastapi import APIRouter
from app.schemas import InsightRequest, InsightResponse
from app.services.rag import answer_with_rag

router = APIRouter(prefix="/insights", tags=["insights"])

@router.post("", response_model=InsightResponse)
def insights(req: InsightRequest):
    """
    POST /insights
    Ask a question about any ingested PDFs and get a concise, cited answer.
    """
    answer, sources = answer_with_rag(req.question, top_k=req.top_k)
    return InsightResponse(answer=answer, sources=sources)
