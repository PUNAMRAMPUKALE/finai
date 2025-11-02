# app/api/v1/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional

# --- Auth ---
class RegisterReq(BaseModel):
    email: EmailStr
    password: str

class LoginReq(BaseModel):
    email: EmailStr
    password: str

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
    firm: Optional[str] = None
    sectors: Optional[str] = ""
    stages: Optional[str] = ""
    geo: Optional[str] = ""
    thesis: Optional[str] = ""
    constraints: Optional[str] = ""
    profile: Optional[str] = ""
    check_min: Optional[float] = None
    check_max: Optional[float] = None
    check_currency: Optional[str] = "USD"

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
    # View Profile → send only name/question, or add mode="profile"
    # Fit/Match → include pitchSummary and/or mode="fit"
    name: str
    question: str = Field(alias="questionText")
    pitch_summary: Optional[str] = Field(default="", alias="pitchSummary")
    mode: Optional[str] = "profile"  # "profile" | "fit"

    class Config:
        populate_by_name = True

class QAResp(BaseModel):
    answer: str
    snippets: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []  # { text, score, citation: {source,title,field} }