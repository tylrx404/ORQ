"""
JWT utility functions for creating and decoding access tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings


class TokenError(Exception):
    """Base exception for token-related errors."""
    pass


class TokenExpiredError(TokenError):
    """Exception raised when a token has expired."""
    pass


class TokenInvalidError(TokenError):
    """Exception raised when a token is invalid or malformed."""
    pass


def create_access_token(subject: str) -> str:
    """
    Create a new JWT access token.

    Args:
        subject: The subject of the token (typically user ID or email).

    Returns:
        The encoded JWT string.

    Raises:
        ValueError: If the subject is empty or only whitespace.
    """
    if not subject or not str(subject).strip():
        raise ValueError("Token subject cannot be empty or whitespace.")

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(subject).strip(),
        "iat": now,
        "exp": expire,
    }
    
    encoded_jwt = jwt.encode(
        payload, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded payload dictionary.

    Raises:
        TokenExpiredError: If the token has expired.
        TokenInvalidError: If the token is invalid, malformed, or missing a valid subject.
    """
    try:
        decoded_payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalidError("Access token is invalid or malformed.") from exc

    subject = decoded_payload.get("sub")
    if not subject or not str(subject).strip():
        raise TokenInvalidError("Token payload is missing a valid 'sub' claim.")

    return decoded_payload
