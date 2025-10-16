# app/api/v1/routers/crew.py
from fastapi import APIRouter
from pydantic import BaseModel
import json

from app.domain.services.crew import build_crew                     # unchanged location after move
from app.domain.services.recommendation import recommend           # ✅ use new LLM recommender

router = APIRouter()

class AdviceReq(BaseModel):
    question: str
    profile: dict

def _task_text(t):
    for k in ("output", "raw_output", "final_output", "result", "value", "content", "raw"):
        v = getattr(t, k, None)
        if v:
            return v
    d = t.model_dump() if hasattr(t, "model_dump") else (t.dict() if hasattr(t, "dict") else {})
    for k in ("output", "raw_output", "final_output", "result", "value", "content", "raw", "text"):
        if k in d and d[k]:
            return d[k]
    return str(t)

def _crew_text(r):
    for k in ("final_output", "output", "results", "result"):
        v = getattr(r, k, None)
        if v:
            return v
    d = r.model_dump() if hasattr(r, "model_dump") else (r.dict() if hasattr(r, "dict") else {})
    for k in ("final_output", "output", "results", "result"):
        if k in d and d[k]:
            return d[k]
    return str(r)

@router.post("/crew/advice")
def crew_advice(req: AdviceReq):
    # Precompute product-match JSON using the new LLM recommender
    match_payload = recommend(req.profile)                 # dict with products + explanation
    tool_json = json.dumps(match_payload)                  # what the agent is instructed to echo

    crew_instance = build_crew()
    result = crew_instance.kickoff(inputs={
        "question": req.question,
        "profile": req.profile,
        "product_match_json": tool_json,                   # passed into the matcher task
    })

    tasks = getattr(result, "tasks_output", []) or []
    research = _task_text(tasks[0]) if len(tasks) > 0 else None
    product_match = _task_text(tasks[1]) if len(tasks) > 1 else None

    return {
        "research": research,
        "product_match": product_match,
        "crew_summary": _crew_text(result),
    }