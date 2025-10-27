# app/db/core.py
import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

# Get URL from env (Render injects it)
raw = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if not raw:
    raise RuntimeError("DATABASE_URL is not set. Configure PostgreSQL in Render or .env.")

# Normalize and enforce driver/SSL for hosted Postgres
db_url = raw.replace("postgres://", "postgresql://")
if db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
if db_url.startswith("postgresql+psycopg2://") and "sslmode=" not in db_url:
    db_url += ("&" if "?" in db_url else "?") + "sslmode=require"

print("✅ DATABASE_URL in use:", db_url)

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)

def init_db() -> None:
    from app.db import models  # ensure tables are imported
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s
