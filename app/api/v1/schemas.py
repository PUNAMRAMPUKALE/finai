from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional

# Auth
class RegisterReq(BaseModel):
    email: EmailStr
    password: str

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: EmailStr

# Ingest investors (JSON)
class InvestorList(BaseModel):
    items: List[Dict[str, Any]]

class IngestResponse(BaseModel):
    inserted: int

# Match (upload pdf → investors)
class MatchResponse(BaseModel):
    matches: List[Dict[str, Any]]