# app/deps.py
from fastapi import Depends, HTTPException, Header
from sqlmodel import Session, select
from app.db.core import get_session
from app.db.models import User
from app.core.security import decode_token

def get_db(session: Session = Depends(get_session)) -> Session:
    return session

def get_current_user(authorization: str | None = Header(default=None),
                     db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        uid = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.exec(select(User).where(User.email == uid)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user