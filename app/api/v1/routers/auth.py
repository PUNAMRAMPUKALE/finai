from fastapi import APIRouter, HTTPException, Header, Depends, Form
from typing import Optional
from sqlmodel import Session, select

from app.api.v1.schemas import RegisterReq, LoginReq, User
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.db.core import get_session
from app.db.models import User as UserModel

router = APIRouter(prefix="/auth", tags=["auth"])

def _get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    return db.exec(select(UserModel).where(UserModel.email == email)).first()

@router.post("/register")
def register(req: RegisterReq, db: Session = Depends(get_session)):
    if _get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="User exists")
    u = UserModel(email=req.email, hashed_password=hash_password(req.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"ok": True}

@router.post("/login")
def login(req: LoginReq, db: Session = Depends(get_session)):
    u = _get_user_by_email(db, req.email)
    if not u or not verify_password(req.password, u.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(sub=u.email)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login-form")
def login_form(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_session)):
    u = _get_user_by_email(db, username)
    if not u or not verify_password(password, u.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(sub=u.email)
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_session)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    email = payload.get("sub")
    u = _get_user_by_email(db, email)
    if not u:
        raise HTTPException(status_code=401, detail="User not found")
    return User(id=str(u.id), email=u.email)

@router.get("/me", response_model=User)
def me(user: User = Depends(get_current_user)):
    return user