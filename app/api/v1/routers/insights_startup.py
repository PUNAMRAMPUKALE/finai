from fastapi import APIRouter
from pydantic import BaseModel
from app.domain.services.rag import answer_from_startup_docs

router = APIRouter(prefix="/api/v1/insights/startup", tags=["rag"])

class InsightsReq(BaseModel):
    question: str
    top_k: int = 5

@router.post("")
def get_startup_insights(req: InsightsReq):
    answer, refs = answer_from_startup_docs(req.question, req.top_k)
    return {"answer": answer, "sources": refs}