from fastapi import Depends
from sqlmodel import Session

from app.db.core import get_session
# Re-export the canonical get_current_user from auth.py so everyone imports from app.deps
from app.api.v1.routers.auth import get_current_user  # single source of truth


def get_db(session: Session = Depends(get_session)) -> Session:
    return session


__all__ = ["get_db", "get_current_user"]