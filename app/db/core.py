import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please configure PostgreSQL in .env.")


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

def init_db() -> None:
    from app.db import models  # ensure tables are registered
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s