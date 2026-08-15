import pytest
import os
from src.websocket.adaptive_encryption import (
    AdaptiveEncryptionEngine,
    EncryptionStrategy,
    StandardEncryptionStrategy,
    StreamingEncryptionStrategy,
    ParallelChunkEncryptionStrategy,
    ExecutionContext,
    EncryptionPolicy,
    SystemProfile,
    encrypt_file,
    decrypt_file,
    EncryptionError,
    DecryptionError,
)
from src.websocket.crypto_utils import generate_ecc_key_pair


@pytest.fixture
def ecc_keys():
    private_key_hex, public_key_hex = generate_ecc_key_pair()
    return private_key_hex, public_key_hex


def test_strategy_selection_with_execution_context():
    engine = AdaptiveEncryptionEngine()
    
    # < 1 MB -> Standard
    ctx_small = ExecutionContext(file_size=500 * 1024)
    strat_small = engine.select_strategy(ctx_small)
    assert isinstance(strat_small, StandardEncryptionStrategy)
    assert strat_small.strategy_name == EncryptionStrategy.STANDARD

    # 1 MB to 10 MB -> Streaming
    ctx_med = ExecutionContext(file_size=2 * 1024 * 1024)
    strat_med = engine.select_strategy(ctx_med)
    assert isinstance(strat_med, StreamingEncryptionStrategy)
    assert strat_med.strategy_name == EncryptionStrategy.STREAMING

    # > 10 MB -> Parallel
    ctx_large = ExecutionContext(file_size=12 * 1024 * 1024)
    strat_large = engine.select_strategy(ctx_large)
    assert isinstance(strat_large, ParallelChunkEncryptionStrategy)
    assert strat_large.strategy_name == EncryptionStrategy.PARALLEL


def test_execution_context_override_policy():
    engine = AdaptiveEncryptionEngine()
    
    # LOW_MEMORY policy forces STREAMING even for large files
    ctx = ExecutionContext(
        file_size=15 * 1024 * 1024,
        policy=EncryptionPolicy.LOW_MEMORY,
        system_profile=SystemProfile.DISABLED
    )
    strat = engine.select_strategy(ctx)
    assert isinstance(strat, StreamingEncryptionStrategy)


def test_standard_encryption_decryption(ecc_keys):
    priv_key, pub_key = ecc_keys
    data = b"Hello world! This is a test file for standard AES-GCM encryption."
    
    res = encrypt_file(data, "test.txt", "text/plain", pub_key)
    meta = res["metadata"]
    
    assert meta["encryption_strategy"] == EncryptionStrategy.STANDARD.value
    assert meta["chunk_count"] == 1
    assert "encrypted_aes_key" in meta
    assert len(meta["nonces"]) == 1
    assert len(meta["auth_tags"]) == 1

    decrypted = decrypt_file(res["ciphertext"], meta, priv_key)
    assert decrypted == data


def test_streaming_encryption_decryption(ecc_keys):
    priv_key, pub_key = ecc_keys
    # Generate 1.5 MB data
    data = os.urandom(int(1.5 * 1024 * 1024))
    
    res = encrypt_file(data, "medium.dat", "application/octet-stream", pub_key)
    meta = res["metadata"]
    
    assert meta["encryption_strategy"] == EncryptionStrategy.STREAMING.value
    assert meta["chunk_count"] > 1
    assert len(meta["nonces"]) == meta["chunk_count"]
    assert len(meta["auth_tags"]) == meta["chunk_count"]

    decrypted = decrypt_file(res["ciphertext"], meta, priv_key)
    assert decrypted == data


def test_parallel_encryption_decryption(ecc_keys):
    priv_key, pub_key = ecc_keys
    # Generate 10.5 MB data (2.625 chunks of 4MB)
    data = os.urandom(int(10.5 * 1024 * 1024))
    
    res = encrypt_file(data, "large.dat", "application/octet-stream", pub_key)
    meta = res["metadata"]
    
    assert meta["encryption_strategy"] == EncryptionStrategy.PARALLEL.value
    assert meta["chunk_count"] == 3
    assert len(meta["nonces"]) == 3
    assert len(meta["auth_tags"]) == 3

    decrypted = decrypt_file(res["ciphertext"], meta, priv_key)
    assert decrypted == data


def test_invalid_decryption_key(ecc_keys):
    priv_key, pub_key = ecc_keys
    wrong_priv_key, _ = generate_ecc_key_pair()
    data = b"Secret data"

    res = encrypt_file(data, "secret.txt", "text/plain", pub_key)
    meta = res["metadata"]

    with pytest.raises(DecryptionError):
        decrypt_file(res["ciphertext"], meta, wrong_priv_key)
