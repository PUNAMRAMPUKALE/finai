from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Dict

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import SQLModel, Field, Column, JSON

# -------------------------
# EXISTING TABLES
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

    __table_args__ = (
        # e.g. dashboard queries filtered by (geo, sectors, stages)
        Index("ix_investor_geo_sectors_stages", "geo", "sectors", "stages"),
    )


class Pitch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
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

    __table_args__ = (
        # fast lookups: “all matches for this pitch ordered by score”
        Index("ix_match_pitch_score", "pitch_id", "score_pct"),
    )


class QAResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    investor_name: str = Field(index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    question: str
    answer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("ix_qa_investor_user_created", "investor_name", "user_id", "created_at"),
    )


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
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("ix_product_type_region", "type", "region"),
    )
