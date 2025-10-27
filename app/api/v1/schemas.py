# app/api/v1/schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional

# --- Auth ---
class RegisterReq(BaseModel):
    email: EmailStr
    password: str
    # optional:
    # full_name: Optional[str] = None

class LoginReq(BaseModel):
    email: EmailStr
    password: str

# ➜ ADD THIS (used by auth.py’s get_current_user/me)
class User(BaseModel):
    id: str | int
    email: EmailStr


# --- Ingest investors ---
class InvestorList(BaseModel):
    items: List[Dict[str, Any]]

class IngestResponse(BaseModel):
    inserted: int

# --- Match ---
class MatchResponse(BaseModel):
    matches: List[Dict[str, Any]]
    query_text: Optional[str] = None

# --- Investor profile / RAG ---
class InvestorProfile(BaseModel):
    name: str
    sectors: Optional[str] = ""
    stages: Optional[str] = ""
    geo: Optional[str] = ""
    checkSize: Optional[str] = ""
    thesis: Optional[str] = ""
    constraints: Optional[str] = ""
    profile: Optional[str] = ""

class AnalysisReq(BaseModel):
    name: str
    pitch_summary: Optional[str] = ""

class AgentBlock(BaseModel):
    agent: str
    summary: str
    bullets: List[str]

class AnalysisResp(BaseModel):
    context_snippets: List[Dict[str, Any]]
    agents: List[AgentBlock]
    score_hint: int

class QAReq(BaseModel):
    name: str
    question: str
    pitch_summary: Optional[str] = ""

class QAResp(BaseModel):
    answer: str
    snippets: List[Dict[str, Any]] = []