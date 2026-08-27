import hashlib
import hmac
import os
import secrets
from typing import Optional

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def generate_session_id() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()


# ── CSRF Protection ──

def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_hex(32)


def verify_csrf_token(token: str, secret: str) -> bool:
    """Verify a CSRF token using HMAC."""
    if not token or not secret:
        return False
    return hmac.compare_digest(token, secret)
