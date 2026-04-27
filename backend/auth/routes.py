"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text

from auth.dependencies import get_current_user
from auth.schemas import TokenResponse, UserLogin, UserPublic, UserRegister
from auth.utils import create_access_token, hash_password, verify_password
from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])



@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister) -> UserPublic:
    """Create a new user. Returns the public profile (no password hash)."""
    with get_connection() as conn:
        # Check for duplicate email / username
        existing = conn.execute(
            text("SELECT id FROM users WHERE email = :email OR username = :username"),
            {"email": body.email, "username": body.username},
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email or username already exists",
            )

        row = conn.execute(
            text(
                """
                INSERT INTO users (email, username, password_hash)
                VALUES (:email, :username, :password_hash)
                RETURNING id, email, username, role, is_active
                """
            ),
            {
                "email": body.email,
                "username": body.username,
                "password_hash": hash_password(body.password),
            },
        ).mappings().one()

    logger.info(f"New user registered: {body.username} ({body.email})")
    return UserPublic(
        id=str(row["id"]),
        email=row["email"],
        username=row["username"],
        role=row["role"],
        is_active=row["is_active"],
    )



@router.post("/token", response_model=TokenResponse)
def login(body: UserLogin) -> TokenResponse:
    """Authenticate and return a JWT access token."""
    with get_connection() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, username, password_hash, role, is_active
                FROM users
                WHERE username = :username
                """
            ),
            {"username": body.username},
        ).mappings().fetchone()

    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not row:
        # Constant-time-ish: still run bcrypt even when user not found to avoid timing attacks.
        # Use a real pre-computed hash of a dummy string.
        verify_password("dummy", "$2b$12$0psZr.w8DJhkVlka0sGVlemcOGU./wuddXKCQbtTgVzAIsFe8rmzO")
        raise invalid_exc

    if not verify_password(body.password, row["password_hash"]):
        raise invalid_exc

    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token, expires_in = create_access_token(
        subject=row["username"],
        role=row["role"],
    )
    logger.info(f"User logged in: {row['username']} (role={row['role']})")
    return TokenResponse(access_token=token, expires_in=expires_in)



@router.get("/me", response_model=UserPublic)
def get_me(current_user: dict = Depends(get_current_user)) -> UserPublic:
    """Return the profile of the currently authenticated user."""
    with get_connection() as conn:
        row = conn.execute(
            text(
                "SELECT id, email, username, role, is_active "
                "FROM users WHERE username = :username"
            ),
            {"username": current_user["sub"]},
        ).mappings().fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserPublic(
        id=str(row["id"]),
        email=row["email"],
        username=row["username"],
        role=row["role"],
        is_active=row["is_active"],
    )
