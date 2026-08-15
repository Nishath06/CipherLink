"""
CipherLink — AES-256-GCM Encryption Service

Provides authenticated symmetric encryption using AES-256-GCM.
"""

import os
import logging
from typing import Dict, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


def generate_aes_key() -> bytes:
    """Generate a cryptographically secure 256-bit AES key."""
    return os.urandom(32)


def aes_encrypt(plaintext: bytes, aes_key: bytes) -> Dict[str, Any]:
    """
    Encrypt data using AES-256-GCM (single pass).

    Returns:
        dict with 'ciphertext', 'nonce' (hex), 'auth_tag' (hex)
    """
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]

    return {
        "ciphertext": ciphertext,
        "nonce": nonce.hex(),
        "auth_tag": tag.hex(),
    }


def aes_decrypt(ciphertext: bytes, nonce_hex: str, auth_tag_hex: str, aes_key: bytes) -> bytes:
    """
    Decrypt AES-256-GCM encrypted data.

    Args:
        ciphertext: The encrypted data (without tag)
        nonce_hex: Hex-encoded 96-bit nonce
        auth_tag_hex: Hex-encoded 128-bit authentication tag
        aes_key: 256-bit AES key

    Returns:
        Decrypted plaintext bytes
    """
    aesgcm = AESGCM(aes_key)
    nonce = bytes.fromhex(nonce_hex)
    tag = bytes.fromhex(auth_tag_hex)
    ct_with_tag = ciphertext + tag
    return aesgcm.decrypt(nonce, ct_with_tag, None)
