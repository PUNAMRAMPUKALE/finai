# app/db/core.py

import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------
# Resolve DATABASE_URL
# ---------------------------------------------------------
raw = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if not raw:
    raise RuntimeError("DATABASE_URL is not set")

# 1) Normalize Postgres URI → psycopg2 driver
url = raw.replace("postgres://", "postgresql://", 1)
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

# 2) Add sslmode=require for cloud DBs (not localhost)
try:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    is_local = host in ("localhost", "127.0.0.1", "::1") or url.startswith("sqlite")

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if not is_local and "sslmode" not in query:
        query["sslmode"] = "require"

    new_query = urlencode(query)
    url = urlunparse(parsed._replace(query=new_query))
except Exception:
    # fallback — don't break app if parsing error
    pass

print("✅ DATABASE_URL in use:", url)

# ---------------------------------------------------------
# SQLite special handling
# ---------------------------------------------------------
connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

# ---------------------------------------------------------
# Connection Pool Settings (Scaling)
# ---------------------------------------------------------
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

engine = create_engine(
    url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
)

# ---------------------------------------------------------
# DB Init + Session
# ---------------------------------------------------------

def init_db() -> None:
    """
    Ensure tables exist. Called at startup in app/main.py.
    """
    from app.db import models  # ensures SQLModel metadata is loaded
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Dependency for FastAPI endpoints.
    """
    with Session(engine) as session:
        yield session
