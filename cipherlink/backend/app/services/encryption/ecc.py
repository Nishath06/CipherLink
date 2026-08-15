"""
CipherLink — ECC Key Management & Key Wrapping Service

Uses secp256k1 ECIES for asymmetric key wrapping (encrypting AES keys).
"""

import logging
from typing import Tuple

from ecies import decrypt as ecies_decrypt, encrypt as ecies_encrypt
from ecies.utils import generate_key

logger = logging.getLogger(__name__)


def generate_ecc_keypair() -> Tuple[str, str]:
    """
    Generate an ECC secp256k1 key pair.

    Returns:
        (public_key_hex, private_key_hex) — both as hex strings
    """
    sk = generate_key()
    private_key_hex = sk.to_hex()
    public_key_hex = sk.public_key.format(compressed=True).hex()
    logger.info(f"Generated ECC keypair: public_key={public_key_hex[:16]}...")
    return public_key_hex, private_key_hex


def ecc_encrypt_key(aes_key: bytes, recipient_public_key_hex: str) -> bytes:
    """
    Encrypt (wrap) an AES key using the recipient's ECC public key (ECIES).

    Args:
        aes_key: The 32-byte AES key to wrap
        recipient_public_key_hex: Hex-encoded compressed secp256k1 public key

    Returns:
        Encrypted AES key bytes
    """
    return ecies_encrypt(recipient_public_key_hex, aes_key)


def ecc_decrypt_key(encrypted_aes_key: bytes, private_key_hex: str) -> bytes:
    """
    Decrypt (unwrap) an AES key using the recipient's ECC private key.

    Args:
        encrypted_aes_key: ECIES-encrypted AES key bytes
        private_key_hex: Hex-encoded secp256k1 private key

    Returns:
        The original 32-byte AES key
    """
    return ecies_decrypt(private_key_hex, encrypted_aes_key)
