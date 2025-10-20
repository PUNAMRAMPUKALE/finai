import os, time, hmac, hashlib, base64, json
from passlib.hash import bcrypt
from app.config import settings

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.verify(pw, hashed)

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_json(obj) -> str:
    return _b64url(json.dumps(obj, separators=(",", ":")).encode())

def create_access_token(sub: str, ttl: int = settings.jwt_ttl_seconds) -> str:
    header  = {"alg": settings.jwt_algo, "typ": "JWT"}
    payload = {"sub": sub, "exp": int(time.time()) + ttl}
    signing_input = f"{_b64url_json(header)}.{_b64url_json(payload)}".encode()
    sig = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{signing_input.decode()}.{_b64url(sig)}"

def decode_token(token: str) -> dict:
    try:
        h, p, s = token.split(".")
        signing_input = f"{h}.{p}".encode()
        sig = base64.urlsafe_b64decode(s + "==")
        exp_sig = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, exp_sig):
            raise ValueError("bad signature")
        payload = json.loads(base64.urlsafe_b64decode(p + "=="))
        if int(time.time()) >= payload.get("exp", 0):
            raise ValueError("expired")
        return payload
    except Exception as e:
        raise ValueError("invalid token") from e