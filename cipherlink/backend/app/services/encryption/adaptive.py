"""
CipherLink — Adaptive Encryption Engine

Selects the optimal encryption strategy based on file size:
  - < 1 MB   → Standard AES-256-GCM
  - 1–10 MB  → Hybrid AES-256-GCM + ECC key wrapping
  - > 10 MB  → Chunked parallel AES-256-GCM + ECC key wrapping

This is the primary entry point for all encryption/decryption operations.
"""

import logging
import os
import time
from typing import Any, Dict, Optional

from app.services.encryption.aes import aes_encrypt, aes_decrypt, generate_aes_key
from app.services.encryption.ecc import ecc_encrypt_key, ecc_decrypt_key
from app.services.encryption.hybrid import hybrid_encrypt, hybrid_decrypt
from app.services.encryption.chunked import chunked_encrypt, chunked_decrypt

logger = logging.getLogger(__name__)

# Strategy thresholds
ONE_MB = 1 * 1024 * 1024
TEN_MB = 10 * 1024 * 1024


def select_strategy(file_size: int) -> str:
    """
    Select the encryption strategy based on file size.

    Returns:
        "STANDARD_AES", "HYBRID_AES_ECC", or "CHUNKED_AES"
    """
    if file_size < ONE_MB:
        return "STANDARD_AES"
    elif file_size <= TEN_MB:
        return "HYBRID_AES_ECC"
    else:
        return "CHUNKED_AES"


def adaptive_encrypt(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    recipient_public_key_hex: str,
    force_strategy: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Encrypt file bytes using the adaptive encryption engine.

    Auto-selects strategy based on file size, or uses force_strategy if provided.

    Returns:
        {
            "ciphertext": bytes,
            "encrypted_aes_key": bytes,
            "metadata": dict,
            "strategy": str,
            "duration_ms": float,
        }
    """
    start = time.monotonic()
    file_size = len(file_bytes)
    strategy = force_strategy or select_strategy(file_size)

    logger.info(
        f"Adaptive encryption: file='{filename}', size={file_size}B, "
        f"mime={mime_type}, strategy={strategy}"
    )

    if strategy == "STANDARD_AES":
        # Pure AES — but still wrap the key with ECC for consistency
        aes_key = generate_aes_key()
        result = aes_encrypt(file_bytes, aes_key)
        encrypted_aes_key = ecc_encrypt_key(aes_key, recipient_public_key_hex)
        metadata = {
            "encryption_strategy": "STANDARD_AES",
            "algorithm": "AES-256-GCM",
            "key_wrap": "ECC-SECP256K1",
            "nonces": [result["nonce"]],
            "auth_tags": [result["auth_tag"]],
            "chunk_count": 1,
            "chunk_size": file_size,
            "filename": filename,
            "mime_type": mime_type,
            "version": "2.0",
        }
        ciphertext = result["ciphertext"]

    elif strategy == "HYBRID_AES_ECC":
        result = hybrid_encrypt(file_bytes, recipient_public_key_hex)
        encrypted_aes_key = result["encrypted_aes_key"]
        metadata = result["metadata"]
        metadata["filename"] = filename
        metadata["mime_type"] = mime_type
        ciphertext = result["ciphertext"]

    elif strategy == "CHUNKED_AES":
        result = chunked_encrypt(file_bytes, recipient_public_key_hex)
        encrypted_aes_key = result["encrypted_aes_key"]
        metadata = result["metadata"]
        metadata["filename"] = filename
        metadata["mime_type"] = mime_type
        ciphertext = result["ciphertext"]

    else:
        raise ValueError(f"Unknown encryption strategy: {strategy}")

    duration_ms = (time.monotonic() - start) * 1000

    return {
        "ciphertext": ciphertext,
        "encrypted_aes_key": encrypted_aes_key,
        "metadata": metadata,
        "strategy": strategy,
        "duration_ms": duration_ms,
    }


def adaptive_decrypt(
    ciphertext: bytes,
    encrypted_aes_key: bytes,
    metadata: Dict[str, Any],
    private_key_hex: str,
) -> bytes:
    """
    Decrypt file using metadata-driven strategy selection.

    Returns:
        Original file bytes
    """
    start = time.monotonic()
    strategy = metadata.get("encryption_strategy")

    logger.info(f"Adaptive decryption: strategy={strategy}")

    if strategy == "STANDARD_AES":
        aes_key = ecc_decrypt_key(encrypted_aes_key, private_key_hex)
        plaintext = aes_decrypt(
            ciphertext,
            metadata["nonces"][0],
            metadata["auth_tags"][0],
            aes_key,
        )

    elif strategy == "HYBRID_AES_ECC":
        plaintext = hybrid_decrypt(ciphertext, encrypted_aes_key, metadata, private_key_hex)

    elif strategy == "CHUNKED_AES":
        plaintext = chunked_decrypt(ciphertext, encrypted_aes_key, metadata, private_key_hex)

    else:
        raise ValueError(f"Unknown encryption strategy: {strategy}")

    duration_ms = (time.monotonic() - start) * 1000
    logger.info(f"Decryption complete in {duration_ms:.1f}ms")

    return plaintext
