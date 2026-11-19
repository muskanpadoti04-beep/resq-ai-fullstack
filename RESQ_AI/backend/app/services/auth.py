"""
RESQ AI - authentication and role-based permissions.

Uses only the Python standard library (no extra packages):
  * passwords are stored as salted PBKDF2-SHA256 hashes
  * login returns a signed HS256 token (standard JWT format) that expires
Roles:  viewer (read only)  <  operator (run incident actions)  <  admin (demo reset, audit log)
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import config
from app.database.db import get_db
from app.models import models as m

ROLE_RANK = {"viewer": 1, "operator": 2, "admin": 3}
_bearer = HTTPBearer(auto_error=False)
_failed = {}  # username -> (count, first_fail_time)


# ---------- passwords ----------
def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hash_password(password, salt).split("$")[2]
    return hmac.compare_digest(candidate, digest)


# ---------- tokens (HS256 JWT) ----------
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(username: str, role: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({
        "sub": username, "role": role,
        "exp": int(time.time()) + config.TOKEN_HOURS * 3600,
    }).encode())
    sig = hmac.new(config.SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(sig)}"


def decode_token(token: str) -> Optional[dict]:
    try:
        header, payload, sig = token.split(".")
        expected = hmac.new(config.SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(sig), expected):
            return None
        data = json.loads(_unb64(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


# ---------- login throttling ----------
def login_locked(username: str) -> bool:
    count, first = _failed.get(username, (0, 0))
    if count >= config.MAX_FAILED_LOGINS:
        if time.time() - first < config.LOCKOUT_SECONDS:
            return True
        _failed.pop(username, None)
    return False


def record_login_result(username: str, ok: bool):
    if ok:
        _failed.pop(username, None)
        return
    count, first = _failed.get(username, (0, time.time()))
    _failed[username] = (count + 1, first)


# ---------- FastAPI dependencies ----------
class CurrentUser:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not config.AUTH_ENABLED:
        return CurrentUser("demo-admin", "admin")
    if creds is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    data = decode_token(creds.credentials)
    if not data:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    user = db.query(m.User).filter(m.User.username == data["sub"]).first()
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="This account is no longer active.")
    return CurrentUser(user.username, user.role)  # role from DB, not from the token


def require_role(minimum: str):
    """Dependency factory: require_role('operator') allows operator and admin."""
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if ROLE_RANK.get(user.role, 0) < ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=403,
                detail=f"Your role ({user.role}) is not allowed to do this. {minimum.title()} access is required.",
            )
        return user
    return checker


DEFAULT_USERS = [
    ("admin", "Administrator", "admin123", "admin"),
    ("operator", "Command Center Operator", "operator123", "operator"),
    ("viewer", "Read-only Viewer", "viewer123", "viewer"),
]


def seed_default_users(db: Session):
    """Demo accounts. Change these passwords before any real use."""
    for username, full_name, password, role in DEFAULT_USERS:
        if not db.query(m.User).filter(m.User.username == username).first():
            db.add(m.User(username=username, full_name=full_name,
                          password_hash=hash_password(password), role=role, active=True))
    db.commit()


def operator_or_device(
    x_device_key: Optional[str] = Header(None),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Sensor gateways authenticate with the X-Device-Key header; people use a normal operator login."""
    if x_device_key is not None:
        if hmac.compare_digest(x_device_key, config.DEVICE_API_KEY):
            return CurrentUser("sensor-gateway", "operator")
        raise HTTPException(status_code=401, detail="Invalid device key.")
    user = get_current_user(creds, db)
    if ROLE_RANK.get(user.role, 0) < ROLE_RANK["operator"]:
        raise HTTPException(status_code=403, detail=f"Your role ({user.role}) is not allowed to do this. Operator access is required.")
    return user
