"""
CipherLink — Security Utilities

Password hashing, JWT token management, and cryptographic helpers.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

from app.core.config import settings

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt directly."""
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    pwd_bytes = plain_password.encode('utf-8')[:72]
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


# ── JWT Tokens ────────────────────────────────────────────────────────────────

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ── Client Credentials ───────────────────────────────────────────────────────

def generate_client_id() -> str:
    """Generate a unique client ID for application registration."""
    return f"cl_app_{secrets.token_hex(16)}"


def generate_client_secret() -> str:
    """Generate a secure client secret."""
    return f"cl_secret_{secrets.token_urlsafe(48)}"


def hash_client_secret(secret: str) -> str:
    """Hash a client secret for storage. Uses SHA-256 for fast lookup."""
    return hashlib.sha256(secret.encode()).hexdigest()


# ── Encryption Master Key ────────────────────────────────────────────────────

def get_master_key_bytes() -> bytes:
    """
    Derive the 32-byte master encryption key from the hex config string.
    Used for encrypting private keys at rest.
    """
    hex_key = settings.ENCRYPTION_MASTER_KEY
    # If key is not 64 hex chars, derive from SHA-256
    if len(hex_key) == 64:
        return bytes.fromhex(hex_key)
    return hashlib.sha256(hex_key.encode()).digest()


def encrypt_private_key(private_key_bytes: bytes) -> bytes:
    """
    Encrypt a private key using the master key (AES-256-GCM).
    Returns: nonce (12 bytes) + ciphertext + tag (16 bytes)
    """
    import os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    master_key = get_master_key_bytes()
    aesgcm = AESGCM(master_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, private_key_bytes, None)
    return nonce + ciphertext


def decrypt_private_key(encrypted_data: bytes) -> bytes:
    """
    Decrypt a private key encrypted with the master key.
    Input: nonce (12 bytes) + ciphertext + tag (16 bytes)
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    master_key = get_master_key_bytes()
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aesgcm = AESGCM(master_key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# ── Request ID ────────────────────────────────────────────────────────────────

def generate_request_id() -> str:
    """Generate a unique request ID for tracing."""
    return secrets.token_hex(16)
