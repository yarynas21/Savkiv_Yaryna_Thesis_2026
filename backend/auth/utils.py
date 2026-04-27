"""
Auth utilities — password hashing and JWT token handling.

Passwords : bcrypt via passlib (work factor 12)
Tokens    : HS256 JWT via python-jose; short-lived access tokens only
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from utils.logger import get_logger

logger = get_logger(__name__)

SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Add it to .env — "
        "generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    """Returns (encoded_jwt, expires_in_seconds)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"JWT issued for '{subject}' (role={role}), expires {expire.isoformat()}")
    return token, ACCESS_TOKEN_EXPIRE_MINUTES * 60


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jose.JWTError on invalid/expired tokens."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
