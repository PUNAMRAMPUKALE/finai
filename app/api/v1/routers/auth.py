from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, Dict
from app.api.v1.schemas import RegisterReq, LoginReq, User
from app.core.security import hash_password, verify_password, create_access_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory user store for demo
_USERS: Dict[str, Dict[str, str]] = {}

@router.post("/register")
def register(req: RegisterReq):
    if req.email in _USERS:
        raise HTTPException(status_code=400, detail="User exists")
    _USERS[req.email] = {"id": req.email, "email": req.email, "hashed": hash_password(req.password)}
    return {"ok": True}

@router.post("/login")
def login(req: LoginReq):
    u = _USERS.get(req.email)
    if not u or not verify_password(req.password, u["hashed"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(sub=u["id"])
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(authorization: Optional[str] = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        uid = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    u = _USERS.get(uid)
    if not u:
        raise HTTPException(status_code=401, detail="User not found")
    return User(id=u["id"], email=u["email"])

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user