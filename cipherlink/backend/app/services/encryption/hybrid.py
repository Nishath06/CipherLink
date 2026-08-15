"""
CipherLink — Hybrid Encryption Service

Combines AES-256-GCM symmetric encryption with ECC key wrapping.
Used for medium-sized files (1 MB – 10 MB).
"""

import logging
import os
from typing import Any, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.services.encryption.ecc import ecc_encrypt_key, ecc_decrypt_key

logger = logging.getLogger(__name__)


def hybrid_encrypt(
    file_bytes: bytes,
    recipient_public_key_hex: str,
) -> Dict[str, Any]:
    """
    Perform hybrid AES-256-GCM + ECC encryption.

    1. Generate random AES-256 key
    2. Encrypt payload with AES-256-GCM
    3. Wrap AES key with recipient's ECC public key via ECIES

    Returns:
        dict with 'ciphertext', 'encrypted_aes_key', and metadata
    """
    aes_key = os.urandom(32)
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)

    ct_with_tag = aesgcm.encrypt(nonce, file_bytes, None)
    ciphertext = ct_with_tag[:-16]
    auth_tag = ct_with_tag[-16:]

    encrypted_aes_key = ecc_encrypt_key(aes_key, recipient_public_key_hex)

    return {
        "ciphertext": ciphertext,
        "encrypted_aes_key": encrypted_aes_key,
        "metadata": {
            "encryption_strategy": "HYBRID_AES_ECC",
            "algorithm": "AES-256-GCM",
            "key_wrap": "ECC-SECP256K1",
            "nonces": [nonce.hex()],
            "auth_tags": [auth_tag.hex()],
            "chunk_count": 1,
            "chunk_size": len(file_bytes),
            "version": "2.0",
        },
    }


def hybrid_decrypt(
    ciphertext: bytes,
    encrypted_aes_key: bytes,
    metadata: Dict[str, Any],
    private_key_hex: str,
) -> bytes:
    """
    Decrypt hybrid AES+ECC encrypted data.

    1. Unwrap AES key with recipient's ECC private key
    2. Decrypt payload with AES-256-GCM
    """
    aes_key = ecc_decrypt_key(encrypted_aes_key, private_key_hex)

    aesgcm = AESGCM(aes_key)
    nonce = bytes.fromhex(metadata["nonces"][0])
    tag = bytes.fromhex(metadata["auth_tags"][0])

    ct_with_tag = ciphertext + tag
    return aesgcm.decrypt(nonce, ct_with_tag, None)
