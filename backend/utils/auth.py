"""
Authentication utilities for OpenRecords.
Handles password hashing, JWT generation, and verification.
"""
import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

from config import settings
from models.auth import AuthContext, TokenPayload

# Argon2 hasher instance
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2 hash."""
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHash):
        return False


def generate_user_id() -> str:
    """Generate a unique user ID."""
    # Generate 8 random bytes and encode as hex
    random_part = secrets.token_hex(6)  # 12 hex characters
    return f"user_{random_part}"


def create_jwt_token(user_id: str, username: str) -> str:
    """
    Create a JWT token for a user.

    Args:
        user_id: The user's unique ID
        username: The user's username

    Returns:
        JWT token string
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.jwt_expiration_days)

    payload = {
        "sub": user_id,
        "username": username,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
    }

    token = jwt.encode(
        payload, settings.openrecords_secret_key, algorithm=settings.jwt_algorithm
    )

    return token


def decode_jwt_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.openrecords_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        return TokenPayload(
            sub=payload["sub"],
            username=payload["username"],
            exp=payload["exp"],
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_jwt_token(token: str) -> Tuple[bool, Optional[AuthContext]]:
    """
    Verify a JWT token and extract auth context.

    Args:
        token: The JWT token string

    Returns:
        Tuple of (is_valid, auth_context)
    """
    payload = decode_jwt_token(token)

    if payload is None:
        return False, None

    # Check expiration
    current_time = int(time.time())
    if payload.exp < current_time:
        return False, None

    auth_context = AuthContext(
        user_id=payload.sub,
        username=payload.username,
    )

    return True, auth_context


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()
