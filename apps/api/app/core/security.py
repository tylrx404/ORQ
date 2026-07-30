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

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return password_hash.verify(password, hashed_password)