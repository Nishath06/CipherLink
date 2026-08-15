"""
CipherLink — Encryption Engine Tests

Tests for all three encryption strategies and the adaptive engine.
"""

import os
import pytest
from app.services.encryption.aes import aes_encrypt, aes_decrypt, generate_aes_key
from app.services.encryption.ecc import generate_ecc_keypair, ecc_encrypt_key, ecc_decrypt_key
from app.services.encryption.hybrid import hybrid_encrypt, hybrid_decrypt
from app.services.encryption.chunked import chunked_encrypt, chunked_decrypt
from app.services.encryption.adaptive import adaptive_encrypt, adaptive_decrypt, select_strategy


class TestAESEncryption:
    """Test AES-256-GCM encryption/decryption."""

    def test_encrypt_decrypt_small_data(self):
        key = generate_aes_key()
        data = b"Hello CipherLink!"
        result = aes_encrypt(data, key)
        decrypted = aes_decrypt(result["ciphertext"], result["nonce"], result["auth_tag"], key)
        assert decrypted == data

    def test_encrypt_decrypt_binary_data(self):
        key = generate_aes_key()
        data = os.urandom(1024)
        result = aes_encrypt(data, key)
        decrypted = aes_decrypt(result["ciphertext"], result["nonce"], result["auth_tag"], key)
        assert decrypted == data

    def test_wrong_key_fails(self):
        key1 = generate_aes_key()
        key2 = generate_aes_key()
        data = b"secret data"
        result = aes_encrypt(data, key1)
        with pytest.raises(Exception):
            aes_decrypt(result["ciphertext"], result["nonce"], result["auth_tag"], key2)

    def test_tampered_ciphertext_fails(self):
        key = generate_aes_key()
        data = b"integrity test"
        result = aes_encrypt(data, key)
        tampered = bytearray(result["ciphertext"])
        tampered[0] ^= 0xFF
        with pytest.raises(Exception):
            aes_decrypt(bytes(tampered), result["nonce"], result["auth_tag"], key)


class TestECCKeyManagement:
    """Test ECC key pair generation and key wrapping."""

    def test_keypair_generation(self):
        pub, priv = generate_ecc_keypair()
        assert len(pub) == 66  # compressed secp256k1 public key (33 bytes hex)
        assert len(priv) == 64  # 32 bytes hex

    def test_key_wrapping(self):
        pub, priv = generate_ecc_keypair()
        aes_key = os.urandom(32)
        encrypted = ecc_encrypt_key(aes_key, pub)
        decrypted = ecc_decrypt_key(encrypted, priv)
        assert decrypted == aes_key


class TestHybridEncryption:
    """Test hybrid AES+ECC encryption."""

    def test_hybrid_encrypt_decrypt(self):
        pub, priv = generate_ecc_keypair()
        data = os.urandom(2 * 1024 * 1024)  # 2 MB
        result = hybrid_encrypt(data, pub)
        decrypted = hybrid_decrypt(result["ciphertext"], result["encrypted_aes_key"], result["metadata"], priv)
        assert decrypted == data

    def test_hybrid_metadata(self):
        pub, priv = generate_ecc_keypair()
        data = os.urandom(1024)
        result = hybrid_encrypt(data, pub)
        assert result["metadata"]["encryption_strategy"] == "HYBRID_AES_ECC"
        assert result["metadata"]["algorithm"] == "AES-256-GCM"
        assert result["metadata"]["key_wrap"] == "ECC-SECP256K1"


class TestChunkedEncryption:
    """Test chunked parallel encryption."""

    def test_chunked_encrypt_decrypt(self):
        pub, priv = generate_ecc_keypair()
        data = os.urandom(12 * 1024 * 1024)  # 12 MB
        result = chunked_encrypt(data, pub, chunk_size=4 * 1024 * 1024)
        decrypted = chunked_decrypt(result["ciphertext"], result["encrypted_aes_key"], result["metadata"], priv)
        assert decrypted == data

    def test_chunk_count(self):
        pub, priv = generate_ecc_keypair()
        data = os.urandom(12 * 1024 * 1024)
        result = chunked_encrypt(data, pub, chunk_size=4 * 1024 * 1024)
        assert result["metadata"]["chunk_count"] == 3


class TestAdaptiveEngine:
    """Test the adaptive encryption engine strategy selection."""

    def test_strategy_selection_small(self):
        assert select_strategy(500 * 1024) == "STANDARD_AES"

    def test_strategy_selection_medium(self):
        assert select_strategy(5 * 1024 * 1024) == "HYBRID_AES_ECC"

    def test_strategy_selection_large(self):
        assert select_strategy(15 * 1024 * 1024) == "CHUNKED_AES"

    def test_adaptive_encrypt_decrypt_small(self):
        pub, priv = generate_ecc_keypair()
        data = os.urandom(100 * 1024)  # 100 KB
        result = adaptive_encrypt(data, "test.txt", "text/plain", pub)
        assert result["strategy"] == "STANDARD_AES"
        decrypted = adaptive_decrypt(result["ciphertext"], result["encrypted_aes_key"], result["metadata"], priv)
        assert decrypted == data

    def test_adaptive_encrypt_decrypt_medium(self):
        pub, priv = generate_ecc_keypair()
        data = os.urandom(3 * 1024 * 1024)  # 3 MB
        result = adaptive_encrypt(data, "image.jpg", "image/jpeg", pub)
        assert result["strategy"] == "HYBRID_AES_ECC"
        decrypted = adaptive_decrypt(result["ciphertext"], result["encrypted_aes_key"], result["metadata"], priv)
        assert decrypted == data

    def test_adaptive_encrypt_decrypt_large(self):
        pub, priv = generate_ecc_keypair()
        data = os.urandom(12 * 1024 * 1024)  # 12 MB
        result = adaptive_encrypt(data, "video.mp4", "video/mp4", pub)
        assert result["strategy"] == "CHUNKED_AES"
        decrypted = adaptive_decrypt(result["ciphertext"], result["encrypted_aes_key"], result["metadata"], priv)
        assert decrypted == data

    def test_empty_file(self):
        pub, priv = generate_ecc_keypair()
        data = b""
        result = adaptive_encrypt(data, "empty.txt", "text/plain", pub)
        decrypted = adaptive_decrypt(result["ciphertext"], result["encrypted_aes_key"], result["metadata"], priv)
        assert decrypted == data
