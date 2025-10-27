# app/api/v1/routers/auth.py
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, Dict

from app.api.v1.schemas import RegisterReq, LoginReq, User
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

# --- Optional DB wiring (auto-fallback to in-memory) ---
_HAS_DB = False
SessionDep = None
UserModel = None
select = None

try:
    from sqlmodel import Session, select as _select
    from app.db.core import get_session
    from app.db.models import User as UserModel  # SQLModel table
    _HAS_DB = True
    SessionDep = Depends(get_session)
    select = _select
except Exception:
    # DB not available; keep using in-memory store
    _HAS_DB = False

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory user store for demo / fallback
_USERS: Dict[str, Dict[str, str]] = {}


# ------------ Helpers ------------
def _mem_get_user(email: str) -> Optional[Dict[str, str]]:
    return _USERS.get(email)

def _mem_create_user(email: str, password: str) -> Dict[str, str]:
    _USERS[email] = {"id": email, "email": email, "hashed": hash_password(password)}
    return _USERS[email]

def _db_get_user_by_email(db: "Session", email: str) -> Optional["UserModel"]:
    return db.exec(select(UserModel).where(UserModel.email == email)).first()

def _db_create_user(db: "Session", email: str, password: str) -> "UserModel":
    u = UserModel(email=email, hashed_password=hash_password(password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ------------ Routes ------------
@router.post("/register")
def register(req: RegisterReq, db: "Session" = SessionDep if _HAS_DB else None):
    """
    Register a user.
    - If DB is configured -> create a row in DB (unique on email).
    - Else -> use in-memory fallback.
    """
    if _HAS_DB:
        # DB path
        if _db_get_user_by_email(db, req.email):
            raise HTTPException(status_code=400, detail="User exists")
        _db_create_user(db, req.email, req.password)
        return {"ok": True}
    else:
        # In-memory fallback (UNCHANGED)
        if req.email in _USERS:
            raise HTTPException(status_code=400, detail="User exists")
        _mem_create_user(req.email, req.password)
        return {"ok": True}


@router.post("/login")
def login(req: LoginReq, db: "Session" = SessionDep if _HAS_DB else None):
    """
    Login:
    - DB path verifies against stored hash in DB
    - Fallback path verifies against _USERS
    Returns: { access_token, token_type }
    """
    if _HAS_DB:
        u = _db_get_user_by_email(db, req.email)
        if not u or not verify_password(req.password, u.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(sub=u.email)
        return {"access_token": token, "token_type": "bearer"}
    else:
        # In-memory fallback (UNCHANGED)
        u = _USERS.get(req.email)
        if not u or not verify_password(req.password, u["hashed"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(sub=u["id"])
        return {"access_token": token, "token_type": "bearer"}


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: "Session" = SessionDep if _HAS_DB else None,
) -> User:
    """
    Extract current user from Bearer token.
    - DB path fetches user row
    - Fallback returns from in-memory store
    Response model remains your original `User` schema.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        uid = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if _HAS_DB:
        u = _db_get_user_by_email(db, uid)
        if not u:
            raise HTTPException(status_code=401, detail="User not found")
        return User(id=str(u.id), email=u.email)
    else:
        # In-memory fallback (UNCHANGED)
        u = _USERS.get(uid)
        if not u:
            raise HTTPException(status_code=401, detail="User not found")
        return User(id=u["id"], email=u["email"])


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user