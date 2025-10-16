# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class IngestDoc(BaseModel):
    title: str
    source: Optional[str] = None
    text: Optional[str] = None
    file_path: Optional[str] = None  # local path to your 10–20 page PDF

class IngestResponse(BaseModel):
    inserted: int  # how many chunks were stored

class Profile(BaseModel):
    profile_id: str
    goal: str
    horizon_years: int
    risk: str
    preferences: List[str] = []
    constraints: List[str] = []

class RecommendRequest(BaseModel):
    profile: Profile
    top_k: int = 5  # how many products to return
    query: Optional[str] = None  # optional natural language query

class RecommendationItem(BaseModel):
    productId: str
    score: float
    rationale: List[str]
    key_stats: Dict[str, Any] = {}
    sources: List[str] = []

class RecommendResponse(BaseModel):
    items: List[RecommendationItem]

class InsightRequest(BaseModel):
    question: str
    top_k: int = 5

class InsightResponse(BaseModel):
    answer: str
    sources: List[str]
