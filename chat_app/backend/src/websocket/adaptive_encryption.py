import enum
import logging
import os
from dataclasses import dataclass
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import psutil
except ImportError:
    psutil = None

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ecies import decrypt as ecies_decrypt, encrypt as ecies_encrypt

# Configure module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class EncryptionStrategy(str, enum.Enum):
    """Supported encryption strategies."""
    STANDARD = "STANDARD"
    STREAMING = "STREAMING"
    PARALLEL = "PARALLEL"


class EncryptionPolicy(str, enum.Enum):
    """Enterprise encryption policies."""
    BALANCED = "BALANCED"
    STRICT_SECURITY = "STRICT_SECURITY"
    LOW_MEMORY = "LOW_MEMORY"
    HIGH_PERFORMANCE = "HIGH_PERFORMANCE"


class SystemProfile(str, enum.Enum):
    """System hardware inspection profile mode."""
    AUTO = "AUTO"          # Auto-detect CPU cores & RAM
    DISABLED = "DISABLED"  # Rely solely on file size / policy thresholds
    MANUAL = "MANUAL"      # Use explicitly defined CPU/RAM thresholds in ExecutionContext


@dataclass
class ExecutionContext:
    """
    Clean execution context object holding encryption parameter thresholds.
    Keeps API signature clean and configurable.
    """
    file_size: int
    mime_type: str = "application/octet-stream"
    policy: EncryptionPolicy = EncryptionPolicy.BALANCED
    system_profile: SystemProfile = SystemProfile.AUTO
    cpu_count: Optional[int] = None
    available_memory_mb: Optional[float] = None


class AdaptiveEncryptionError(Exception):
    """Base exception for adaptive encryption errors."""
    pass


class EncryptionError(AdaptiveEncryptionError):
    """Raised when an encryption operation fails."""
    pass


class DecryptionError(AdaptiveEncryptionError):
    """Raised when a decryption operation fails."""
    pass


class StrategySelectionError(AdaptiveEncryptionError):
    """Raised when strategy selection fails."""
    pass


class BaseEncryptionStrategy(ABC):
    """Abstract base class for all encryption strategies."""

    @property
    @abstractmethod
    def strategy_name(self) -> EncryptionStrategy:
        """Return the Enum strategy name."""
        pass

    @abstractmethod
    def encrypt(self, file_bytes: bytes, aes_key: bytes) -> Dict[str, Any]:
        """
        Encrypt file bytes using the given 256-bit AES key.
        Returns a dictionary containing encrypted payload and strategy metadata.
        """
        pass

    @abstractmethod
    def decrypt(self, encrypted_payload: bytes, metadata: Dict[str, Any], aes_key: bytes) -> bytes:
        """
        Decrypt encrypted payload using metadata and 256-bit AES key.
        Returns original file bytes.
        """
        pass


class StandardEncryptionStrategy(BaseEncryptionStrategy):
    """
    Standard AES-256-GCM strategy for single-pass file encryption.
    Encrypts the entire payload at once.
    """

    @property
    def strategy_name(self) -> EncryptionStrategy:
        return EncryptionStrategy.STANDARD

    def encrypt(self, file_bytes: bytes, aes_key: bytes) -> Dict[str, Any]:
        try:
            logger.debug("Executing StandardEncryptionStrategy encryption...")
            aesgcm = AESGCM(aes_key)
            nonce = os.urandom(12)  # 96-bit nonce standard for AES-GCM
            ciphertext_with_tag = aesgcm.encrypt(nonce, file_bytes, None)
            ciphertext = ciphertext_with_tag[:-16]
            tag = ciphertext_with_tag[-16:]

            return {
                "ciphertext": ciphertext,
                "metadata": {
                    "encryption_strategy": self.strategy_name.value,
                    "nonces": [nonce.hex()],
                    "auth_tags": [tag.hex()],
                    "chunk_count": 1,
                    "chunk_size": len(file_bytes),
                    "algorithm": "AES-256-GCM",
                    "version": "2.0",
                },
            }
        except Exception as e:
            logger.error(f"Standard encryption failed: {e}")
            raise EncryptionError(f"Standard encryption failed: {e}") from e

    def decrypt(self, encrypted_payload: bytes, metadata: Dict[str, Any], aes_key: bytes) -> bytes:
        try:
            logger.debug("Executing StandardEncryptionStrategy decryption...")
            aesgcm = AESGCM(aes_key)
            nonce_hex = metadata["nonces"][0]
            tag_hex = metadata["auth_tags"][0]
            nonce = bytes.fromhex(nonce_hex)
            tag = bytes.fromhex(tag_hex)

            ciphertext_with_tag = encrypted_payload + tag
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
            return decrypted_bytes
        except Exception as e:
            logger.error(f"Standard decryption failed: {e}")
            raise DecryptionError(f"Standard decryption failed: {e}") from e


class StreamingEncryptionStrategy(BaseEncryptionStrategy):
    """
    Chunked Stream AES-256-GCM strategy for medium files or memory-constrained environments.
    Reads and encrypts file in fixed-size chunks (64 KB).
    Each chunk is protected with its own unique 96-bit nonce and authentication tag.
    """

    def __init__(self, chunk_size: int = 64 * 1024):
        self.chunk_size = chunk_size  # 64 KB default

    @property
    def strategy_name(self) -> EncryptionStrategy:
        return EncryptionStrategy.STREAMING

    def encrypt(self, file_bytes: bytes, aes_key: bytes) -> Dict[str, Any]:
        try:
            logger.debug("Executing StreamingEncryptionStrategy encryption...")
            aesgcm = AESGCM(aes_key)
            nonces = []
            auth_tags = []
            encrypted_chunks = []

            total_len = len(file_bytes)
            offset = 0

            while offset < total_len or total_len == 0:
                chunk = file_bytes[offset : offset + self.chunk_size]
                chunk_nonce = os.urandom(12)
                ciphertext_with_tag = aesgcm.encrypt(chunk_nonce, chunk, None)
                chunk_ciphertext = ciphertext_with_tag[:-16]
                chunk_tag = ciphertext_with_tag[-16:]

                nonces.append(chunk_nonce.hex())
                auth_tags.append(chunk_tag.hex())
                encrypted_chunks.append(chunk_ciphertext)

                offset += self.chunk_size
                if offset >= total_len and total_len > 0:
                    break

            combined_ciphertext = b"".join(encrypted_chunks)

            return {
                "ciphertext": combined_ciphertext,
                "metadata": {
                    "encryption_strategy": self.strategy_name.value,
                    "nonces": nonces,
                    "auth_tags": auth_tags,
                    "chunk_count": len(encrypted_chunks),
                    "chunk_size": self.chunk_size,
                    "algorithm": "AES-256-GCM",
                    "version": "2.0",
                },
            }
        except Exception as e:
            logger.error(f"Streaming encryption failed: {e}")
            raise EncryptionError(f"Streaming encryption failed: {e}") from e

    def decrypt(self, encrypted_payload: bytes, metadata: Dict[str, Any], aes_key: bytes) -> bytes:
        try:
            logger.debug("Executing StreamingEncryptionStrategy decryption...")
            aesgcm = AESGCM(aes_key)
            nonces = metadata["nonces"]
            auth_tags = metadata["auth_tags"]
            chunk_count = metadata["chunk_count"]
            chunk_size = metadata.get("chunk_size", self.chunk_size)

            decrypted_chunks = []
            payload_offset = 0

            for i in range(chunk_count):
                nonce = bytes.fromhex(nonces[i])
                tag = bytes.fromhex(auth_tags[i])

                if i == chunk_count - 1:
                    chunk_ct = encrypted_payload[payload_offset:]
                else:
                    chunk_ct = encrypted_payload[payload_offset : payload_offset + chunk_size]

                payload_offset += len(chunk_ct)
                ciphertext_with_tag = chunk_ct + tag
                chunk_decrypted = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
                decrypted_chunks.append(chunk_decrypted)

            return b"".join(decrypted_chunks)
        except Exception as e:
            logger.error(f"Streaming decryption failed: {e}")
            raise DecryptionError(f"Streaming decryption failed: {e}") from e


class ParallelChunkEncryptionStrategy(BaseEncryptionStrategy):
    """
    Parallel Chunk AES-256-GCM strategy for large files.
    Splits into 4 MB chunks and encrypts in parallel using ThreadPoolExecutor.
    """

    def __init__(self, chunk_size: int = 4 * 1024 * 1024, max_workers: int = 4):
        self.chunk_size = chunk_size  # 4 MB default
        self.max_workers = max_workers

    @property
    def strategy_name(self) -> EncryptionStrategy:
        return EncryptionStrategy.PARALLEL

    def _encrypt_single_chunk(self, chunk_idx: int, chunk_bytes: bytes, aes_key: bytes) -> Tuple[int, bytes, str, str]:
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)
        ct_with_tag = aesgcm.encrypt(nonce, chunk_bytes, None)
        ciphertext = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]
        return (chunk_idx, ciphertext, nonce.hex(), tag.hex())

    def _decrypt_single_chunk(
        self, chunk_idx: int, chunk_ct: bytes, nonce_hex: str, tag_hex: str, aes_key: bytes
    ) -> Tuple[int, bytes]:
        aesgcm = AESGCM(aes_key)
        nonce = bytes.fromhex(nonce_hex)
        tag = bytes.fromhex(tag_hex)
        ct_with_tag = chunk_ct + tag
        decrypted = aesgcm.decrypt(nonce, ct_with_tag, None)
        return (chunk_idx, decrypted)

    def encrypt(self, file_bytes: bytes, aes_key: bytes) -> Dict[str, Any]:
        try:
            logger.debug("Executing ParallelChunkEncryptionStrategy encryption...")
            total_len = len(file_bytes)
            chunks = []
            offset = 0
            chunk_idx = 0

            while offset < total_len or total_len == 0:
                chunk = file_bytes[offset : offset + self.chunk_size]
                chunks.append((chunk_idx, chunk))
                offset += self.chunk_size
                chunk_idx += 1
                if offset >= total_len and total_len > 0:
                    break

            results: List[Optional[Tuple[int, bytes, str, str]]] = [None] * len(chunks)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self._encrypt_single_chunk, idx, chunk_data, aes_key)
                    for idx, chunk_data in chunks
                ]
                for future in as_completed(futures):
                    res = future.result()
                    results[res[0]] = res

            nonces = [res[2] for res in results if res is not None]
            auth_tags = [res[3] for res in results if res is not None]
            encrypted_chunks = [res[1] for res in results if res is not None]
            chunk_lengths = [len(ct) for ct in encrypted_chunks]

            combined_ciphertext = b"".join(encrypted_chunks)

            return {
                "ciphertext": combined_ciphertext,
                "metadata": {
                    "encryption_strategy": self.strategy_name.value,
                    "nonces": nonces,
                    "auth_tags": auth_tags,
                    "chunk_count": len(chunks),
                    "chunk_size": self.chunk_size,
                    "chunk_lengths": chunk_lengths,
                    "algorithm": "AES-256-GCM",
                    "version": "2.0",
                },
            }
        except Exception as e:
            logger.error(f"Parallel chunk encryption failed: {e}")
            raise EncryptionError(f"Parallel chunk encryption failed: {e}") from e

    def decrypt(self, encrypted_payload: bytes, metadata: Dict[str, Any], aes_key: bytes) -> bytes:
        try:
            logger.debug("Executing ParallelChunkEncryptionStrategy decryption...")
            nonces = metadata["nonces"]
            auth_tags = metadata["auth_tags"]
            chunk_count = metadata["chunk_count"]
            chunk_size = metadata.get("chunk_size", self.chunk_size)
            chunk_lengths = metadata.get("chunk_lengths")

            payload_offset = 0
            chunks_to_decrypt = []

            for i in range(chunk_count):
                if chunk_lengths:
                    c_len = chunk_lengths[i]
                else:
                    c_len = chunk_size if i < chunk_count - 1 else len(encrypted_payload) - payload_offset

                chunk_ct = encrypted_payload[payload_offset : payload_offset + c_len]
                payload_offset += c_len
                chunks_to_decrypt.append((i, chunk_ct, nonces[i], auth_tags[i]))

            results: List[Optional[Tuple[int, bytes]]] = [None] * chunk_count

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self._decrypt_single_chunk, idx, c_ct, n_hex, t_hex, aes_key)
                    for idx, c_ct, n_hex, t_hex in chunks_to_decrypt
                ]
                for future in as_completed(futures):
                    res = future.result()
                    results[res[0]] = res

            decrypted_chunks = [res[1] for res in results if res is not None]
            return b"".join(decrypted_chunks)
        except Exception as e:
            logger.error(f"Parallel chunk decryption failed: {e}")
            raise DecryptionError(f"Parallel chunk decryption failed: {e}") from e


class AdaptiveEncryptionEngine:
    """
    Adaptive Encryption Engine utilizing configurable ExecutionContext.
    Decouples strategy selection and system inspection logic.
    """

    ONE_MB = 1 * 1024 * 1024
    TEN_MB = 10 * 1024 * 1024

    def __init__(self):
        self._strategies: Dict[EncryptionStrategy, BaseEncryptionStrategy] = {
            EncryptionStrategy.STANDARD: StandardEncryptionStrategy(),
            EncryptionStrategy.STREAMING: StreamingEncryptionStrategy(chunk_size=64 * 1024),
            EncryptionStrategy.PARALLEL: ParallelChunkEncryptionStrategy(chunk_size=4 * 1024 * 1024),
        }

    def register_strategy(self, strategy_enum: EncryptionStrategy, strategy: BaseEncryptionStrategy) -> None:
        """Register or override a strategy dynamically."""
        self._strategies[strategy_enum] = strategy

    def select_strategy(self, context: ExecutionContext) -> BaseEncryptionStrategy:
        """
        Strategy Selection using ExecutionContext.
        Optionally evaluates hardware metrics based on system_profile setting.
        """
        file_size = context.file_size
        mime_type = context.mime_type
        policy = context.policy
        profile = context.system_profile

        cpu_count = context.cpu_count
        available_memory_mb = context.available_memory_mb

        # System inspection rule: only evaluate hardware if AUTO mode is set and values not manually passed
        if profile == SystemProfile.AUTO:
            if cpu_count is None:
                cpu_count = os.cpu_count() or 2
            if available_memory_mb is None:
                try:
                    if psutil is not None:
                        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
                    else:
                        available_memory_mb = 1024.0
                except Exception:
                    available_memory_mb = 1024.0
        elif profile == SystemProfile.DISABLED:
            # Inspection disabled: set neutral defaults
            cpu_count = cpu_count or 4
            available_memory_mb = available_memory_mb or 2048.0

        logger.info(
            f"Selecting strategy via ExecutionContext: size={file_size}B, mime={mime_type}, "
            f"policy={policy.value}, profile={profile.value}, cpus={cpu_count}, mem={available_memory_mb}MB"
        )

        # Policy Rule 1: LOW_MEMORY policy -> STREAMING
        if policy == EncryptionPolicy.LOW_MEMORY:
            strategy_key = EncryptionStrategy.STREAMING

        # Policy Rule 2: Large media stream files > 5 MB with parallel capability
        elif (mime_type.startswith("video/") or mime_type.startswith("audio/")) and file_size > 5 * self.ONE_MB:
            if cpu_count and cpu_count >= 2 and available_memory_mb and available_memory_mb >= 512.0:
                strategy_key = EncryptionStrategy.PARALLEL
            else:
                strategy_key = EncryptionStrategy.STREAMING

        # Policy Rule 3: Size based defaults
        elif file_size < self.ONE_MB:
            strategy_key = EncryptionStrategy.STANDARD
        elif file_size <= self.TEN_MB:
            strategy_key = EncryptionStrategy.STREAMING
        else:
            if cpu_count and cpu_count >= 2 and available_memory_mb and available_memory_mb >= 512.0:
                strategy_key = EncryptionStrategy.PARALLEL
            else:
                strategy_key = EncryptionStrategy.STREAMING

        strategy = self._strategies.get(strategy_key)
        if not strategy:
            raise StrategySelectionError(f"No strategy registered for {strategy_key}")

        logger.info(f"ExecutionContext strategy selected: '{strategy_key.value}'")
        return strategy

    def encrypt(
        self,
        file_bytes: bytes,
        recipient_ecc_public_key_hex: str,
        filename: str = "",
        mime_type: str = "",
        context: Optional[ExecutionContext] = None,
    ) -> Dict[str, Any]:
        """
        Encrypt file bytes adaptively using optional ExecutionContext.
        """
        try:
            logger.info(f"Starting adaptive encryption for file '{filename}' ({len(file_bytes)} bytes)")
            aes_key = os.urandom(32)

            if context is None:
                context = ExecutionContext(
                    file_size=len(file_bytes),
                    mime_type=mime_type,
                    policy=EncryptionPolicy.BALANCED,
                    system_profile=SystemProfile.AUTO,
                )

            strategy = self.select_strategy(context)
            result = strategy.encrypt(file_bytes, aes_key)

            encrypted_aes_key = ecies_encrypt(recipient_ecc_public_key_hex, aes_key)

            metadata = result["metadata"]
            metadata["encrypted_aes_key"] = encrypted_aes_key.hex()
            metadata["filename"] = filename
            metadata["mime_type"] = mime_type
            metadata["version"] = "2.0"

            return {
                "ciphertext": result["ciphertext"],
                "metadata": metadata,
                "encrypted_aes_key_bytes": encrypted_aes_key,
            }
        except AdaptiveEncryptionError:
            raise
        except Exception as e:
            logger.exception(f"Adaptive encryption failed unexpectedly: {e}")
            raise EncryptionError(f"Adaptive encryption failed: {e}") from e

    def decrypt(
        self, ciphertext: bytes, metadata: Dict[str, Any], recipient_ecc_private_key_hex: str
    ) -> bytes:
        """
        Decrypt file adaptively with multi-version backwards compatibility.
        """
        try:
            version = metadata.get("version", "1.0")
            logger.info(f"Executing adaptive decryption for payload metadata version: {version}")

            strategy_str = metadata.get("encryption_strategy")
            if not strategy_str:
                raise DecryptionError("Metadata missing 'encryption_strategy'")

            try:
                strategy_key = EncryptionStrategy(strategy_str)
            except ValueError as ve:
                raise DecryptionError(f"Unknown encryption strategy: {strategy_str}") from ve

            strategy = self._strategies.get(strategy_key)
            if not strategy:
                raise DecryptionError(f"Strategy {strategy_key} is not supported by engine")

            encrypted_aes_key_hex = metadata.get("encrypted_aes_key")
            if not encrypted_aes_key_hex:
                raise DecryptionError("Metadata missing 'encrypted_aes_key'")

            encrypted_aes_key = bytes.fromhex(encrypted_aes_key_hex)
            aes_key = ecies_decrypt(recipient_ecc_private_key_hex, encrypted_aes_key)

            return strategy.decrypt(ciphertext, metadata, aes_key)
        except AdaptiveEncryptionError:
            raise
        except Exception as e:
            logger.exception(f"Adaptive decryption failed unexpectedly: {e}")
            raise DecryptionError(f"Adaptive decryption failed: {e}") from e


# Global Engine Instance
_engine = AdaptiveEncryptionEngine()


def encrypt_file(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    recipient_ecc_public_key_hex: str,
    context: Optional[ExecutionContext] = None,
) -> Dict[str, Any]:
    """
    Standard high-level entrypoint with optional ExecutionContext.
    """
    return _engine.encrypt(
        file_bytes,
        recipient_ecc_public_key_hex,
        filename=filename,
        mime_type=mime_type,
        context=context,
    )


def decrypt_file(
    ciphertext: bytes,
    metadata: Dict[str, Any],
    recipient_ecc_private_key_hex: str,
) -> bytes:
    """
    Standard high-level entrypoint for file decryption.
    """
    return _engine.decrypt(ciphertext, metadata, recipient_ecc_private_key_hex)
