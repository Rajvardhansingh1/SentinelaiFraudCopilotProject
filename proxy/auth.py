"""Phase 2 (D-055): authentication. Bcrypt password hashing, stateless JWT
sessions (no server-side session store, no refresh-token flow — YAGNI for
V1; a caller "logs out" by discarding its token, same ceiling most JWT
setups start with). No admin role/authorization system beyond "is this the
project's owner" — spec_V3.md Phase 2 asks for account + project isolation,
not RBAC.

ponytail: no refresh tokens, no server-side revocation list. Upgrade path if
needed: a `token_version` column on User, bumped on password change, checked
in verify_token()."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator

from proxy.config import settings
from proxy.db.models import User
from proxy.db.session import get_session

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8

# A missing JWT_SECRET in production is a hard stop (proxy/main.py checks
# this at import time); for local dev/tests, a per-process random secret is
# fine — tokens just don't survive a restart, which is the correct trade-off
# for "don't require every contributor to configure a secret to run tests."
_EFFECTIVE_JWT_SECRET = settings.jwt_secret or secrets.token_hex(32)

_bearer_scheme = HTTPBearer(auto_error=False)


class SignupRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Not a valid email address.")
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password_length(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False  # malformed hash — never let a bad row 500 the login endpoint


def issue_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=settings.jwt_expiry_hours)}
    return jwt.encode(payload, _EFFECTIVE_JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, _EFFECTIVE_JWT_SECRET, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail={"code": "invalid_token", "message": "Invalid or expired token."})


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail={"code": "not_authenticated", "message": "Missing bearer token."})
    user_id = decode_token(credentials.credentials)
    db = get_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail={"code": "user_not_found", "message": "Token references a deleted account."})
        db.expunge(user)  # detach — caller's own db session (if any) shouldn't inherit this one's lifecycle
        return user
    finally:
        db.close()
