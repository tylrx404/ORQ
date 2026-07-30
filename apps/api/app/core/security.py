"""
app/core/security.py
--------------------

Security utilities for authentication.

Responsibilities
----------------
- Hash plain-text passwords.
- Verify passwords against stored hashes.

Notes
-----
- Never store plain-text passwords.
- Password hashing is intentionally slow to resist brute-force attacks.
- This module contains NO JWT logic.
- This module contains NO authentication APIs.
"""

from pwdlib import PasswordHash

# Single password hasher instance used throughout the application.
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password.

    Args:
        password: User's plain-text password.

    Returns:
        Secure password hash suitable for database storage.
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against its stored hash.

    Args:
        password: Password entered by the user.
        hashed_password: Password hash stored in the database.

    Returns:
        True if the password matches, otherwise False.
    """
    if not password or not hashed_password:
        return False

    return password_hash.verify(password, hashed_password)