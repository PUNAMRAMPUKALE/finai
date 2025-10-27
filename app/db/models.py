from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Dict


from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import SQLModel, Field


from sqlmodel import Field, SQLModel, Column, JSON
# -------------------------
# EXISTING TABLES (unchanged)
# -------------------------

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    hashed_password: str
    role: str = "founder"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Investor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    firm: Optional[str] = None
    sectors: Optional[str] = None
    stages: Optional[str] = None
    geo: Optional[str] = None
    check_min: Optional[float] = None
    check_max: Optional[float] = None
    check_currency: Optional[str] = None
    thesis: Optional[str] = None
    constraints: Optional[str] = None
    weaviate_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Pitch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    file_path: str
    summary: str
    vector_id: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pitch_id: int = Field(foreign_key="pitch.id", index=True)
    investor_name: str = Field(index=True)
    score_pct: int
    distance: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QAResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    investor_name: str = Field(index=True)
    user_id: int = Field(foreign_key="user.id")
    question: str
    answer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# -------------------------
# NEW TABLES (additive only)
# -------------------------


# ... keep your other models as-is ...


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(index=True, unique=True)
    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    terms: Optional[str] = None
    fees: Optional[str] = None
    eligibility: Optional[str] = None
    risk_label: Optional[str] = None
    meta: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    # ✅ add this line
    created_at: datetime = Field(default_factory=datetime.utcnow)