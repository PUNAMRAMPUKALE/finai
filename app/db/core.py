# app/db/core.py
import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

raw = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if not raw:
    raise RuntimeError("DATABASE_URL is not set")

# 1) Normalize driver (postgres -> postgresql+psycopg2)
url = raw.replace("postgres://", "postgresql://", 1)
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

# 2) Append sslmode=require ONLY for non-local hosts
try:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    is_local = host in ("localhost", "127.0.0.1", "::1") or url.startswith("sqlite")

    # rebuild query params
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if not is_local and "sslmode" not in q:
        q["sslmode"] = "require"

    new_query = urlencode(q)
    url = urlunparse(parsed._replace(query=new_query))
except Exception:
    # if parsing fails, fall back to whatever we had
    pass

print("✅ DATABASE_URL in use:", url)

connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)

def init_db() -> None:
    from app.db import models  # ensure table metadata is registered
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s
