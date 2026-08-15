"""
CipherLink — Chunked Encryption Service

Parallel chunk-based AES-256-GCM encryption for large files (> 10 MB).
Splits files into configurable chunks and encrypts them concurrently.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.services.encryption.ecc import ecc_encrypt_key, ecc_decrypt_key

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB
DEFAULT_MAX_WORKERS = 4


def _encrypt_chunk(
    chunk_idx: int, chunk_bytes: bytes, aes_key: bytes
) -> Tuple[int, bytes, str, str]:
    """Encrypt a single chunk using AES-256-GCM with a unique nonce."""
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)
    ct_with_tag = aesgcm.encrypt(nonce, chunk_bytes, None)
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    return (chunk_idx, ciphertext, nonce.hex(), tag.hex())


def _decrypt_chunk(
    chunk_idx: int, chunk_ct: bytes, nonce_hex: str, tag_hex: str, aes_key: bytes
) -> Tuple[int, bytes]:
    """Decrypt a single chunk."""
    aesgcm = AESGCM(aes_key)
    nonce = bytes.fromhex(nonce_hex)
    tag = bytes.fromhex(tag_hex)
    ct_with_tag = chunk_ct + tag
    decrypted = aesgcm.decrypt(nonce, ct_with_tag, None)
    return (chunk_idx, decrypted)


def chunked_encrypt(
    file_bytes: bytes,
    recipient_public_key_hex: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> Dict[str, Any]:
    """
    Encrypt a large file using parallel chunked AES-256-GCM + ECC key wrapping.

    1. Generate random AES key
    2. Split file into chunks
    3. Encrypt each chunk in parallel with unique nonces
    4. Wrap the AES key with ECC

    Returns:
        dict with 'ciphertext', 'encrypted_aes_key', and metadata
    """
    aes_key = os.urandom(32)
    total_len = len(file_bytes)

    # Split into chunks
    chunks: List[Tuple[int, bytes]] = []
    offset = 0
    idx = 0
    while offset < total_len:
        chunk = file_bytes[offset : offset + chunk_size]
        chunks.append((idx, chunk))
        offset += chunk_size
        idx += 1

    # Parallel encryption
    results: List[Optional[Tuple[int, bytes, str, str]]] = [None] * len(chunks)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_encrypt_chunk, c_idx, c_data, aes_key)
            for c_idx, c_data in chunks
        ]
        for future in as_completed(futures):
            res = future.result()
            results[res[0]] = res

    nonces = [r[2] for r in results if r is not None]
    auth_tags = [r[3] for r in results if r is not None]
    encrypted_chunks = [r[1] for r in results if r is not None]
    chunk_lengths = [len(ct) for ct in encrypted_chunks]

    combined_ciphertext = b"".join(encrypted_chunks)
    encrypted_aes_key = ecc_encrypt_key(aes_key, recipient_public_key_hex)

    return {
        "ciphertext": combined_ciphertext,
        "encrypted_aes_key": encrypted_aes_key,
        "metadata": {
            "encryption_strategy": "CHUNKED_AES",
            "algorithm": "AES-256-GCM",
            "key_wrap": "ECC-SECP256K1",
            "nonces": nonces,
            "auth_tags": auth_tags,
            "chunk_count": len(chunks),
            "chunk_size": chunk_size,
            "chunk_lengths": chunk_lengths,
            "version": "2.0",
        },
    }


def chunked_decrypt(
    ciphertext: bytes,
    encrypted_aes_key: bytes,
    metadata: Dict[str, Any],
    private_key_hex: str,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> bytes:
    """
    Decrypt a chunked-encrypted file in parallel.

    1. Unwrap AES key with ECC private key
    2. Split combined ciphertext using chunk_lengths
    3. Decrypt each chunk in parallel
    4. Reassemble
    """
    aes_key = ecc_decrypt_key(encrypted_aes_key, private_key_hex)

    nonces = metadata["nonces"]
    auth_tags = metadata["auth_tags"]
    chunk_count = metadata["chunk_count"]
    chunk_lengths = metadata.get("chunk_lengths")
    chunk_size = metadata.get("chunk_size", DEFAULT_CHUNK_SIZE)

    # Split combined ciphertext into individual chunks
    payload_offset = 0
    chunks_to_decrypt = []
    for i in range(chunk_count):
        if chunk_lengths:
            c_len = chunk_lengths[i]
        else:
            c_len = chunk_size if i < chunk_count - 1 else len(ciphertext) - payload_offset
        chunk_ct = ciphertext[payload_offset : payload_offset + c_len]
        payload_offset += c_len
        chunks_to_decrypt.append((i, chunk_ct, nonces[i], auth_tags[i]))

    # Parallel decryption
    results: List[Optional[Tuple[int, bytes]]] = [None] * chunk_count
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_decrypt_chunk, idx, c_ct, n_hex, t_hex, aes_key)
            for idx, c_ct, n_hex, t_hex in chunks_to_decrypt
        ]
        for future in as_completed(futures):
            res = future.result()
            results[res[0]] = res

    decrypted_chunks = [r[1] for r in results if r is not None]
    return b"".join(decrypted_chunks)
