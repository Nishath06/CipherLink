"""
CipherLink — Key Management Service

ECC key pair generation, encrypted storage, rotation, and revocation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_private_key, decrypt_private_key
from app.models.models import EncryptionKey, KeyType, KeyStatus
from app.services.encryption.ecc import generate_ecc_keypair

logger = logging.getLogger(__name__)


async def create_key(
    db: AsyncSession,
    organization_id: int,
    key_type: str,
    algorithm: str = "secp256k1",
    label: Optional[str] = None,
) -> Tuple[EncryptionKey, Optional[str]]:
    """
    Create a new encryption key.

    For ECC keys: generates keypair, encrypts private key with master key.
    Returns (key_model, private_key_hex_or_none).
    The private key hex is returned ONLY on creation for client-side use.
    """
    private_key_hex = None

    if key_type == "ecc":
        public_key_hex, priv_hex = generate_ecc_keypair()
        private_key_hex = priv_hex
        encrypted_priv = encrypt_private_key(bytes.fromhex(priv_hex))

        key = EncryptionKey(
            organization_id=organization_id,
            key_type=KeyType.ECC,
            algorithm=algorithm,
            status=KeyStatus.ACTIVE,
            public_key_hex=public_key_hex,
            encrypted_private_key=encrypted_priv,
            label=label,
        )
    elif key_type == "aes":
        import os
        aes_key = os.urandom(32)
        encrypted_material = encrypt_private_key(aes_key)

        key = EncryptionKey(
            organization_id=organization_id,
            key_type=KeyType.AES,
            algorithm="AES-256-GCM",
            status=KeyStatus.ACTIVE,
            encrypted_key_material=encrypted_material,
            label=label,
        )
    else:
        raise ValueError(f"Unsupported key type: {key_type}")

    db.add(key)
    await db.flush()
    await db.refresh(key)

    logger.info(f"Created {key_type} key: uuid={key.uuid}, org={organization_id}")
    return key, private_key_hex


async def get_keys(
    db: AsyncSession,
    organization_id: int,
    key_type: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    """Get all keys for an organization, optionally filtered."""
    query = select(EncryptionKey).where(
        EncryptionKey.organization_id == organization_id
    )
    if key_type:
        query = query.where(EncryptionKey.key_type == key_type)
    if status:
        query = query.where(EncryptionKey.status == status)

    query = query.order_by(EncryptionKey.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_key_by_uuid(
    db: AsyncSession,
    key_uuid: UUID,
    organization_id: int,
) -> Optional[EncryptionKey]:
    """Get a specific key by UUID, scoped to organization."""
    result = await db.execute(
        select(EncryptionKey).where(
            EncryptionKey.uuid == key_uuid,
            EncryptionKey.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def get_active_ecc_key(
    db: AsyncSession,
    organization_id: int,
) -> Optional[EncryptionKey]:
    """Get the most recent active ECC key for an organization."""
    result = await db.execute(
        select(EncryptionKey).where(
            EncryptionKey.organization_id == organization_id,
            EncryptionKey.key_type == KeyType.ECC,
            EncryptionKey.status == KeyStatus.ACTIVE,
        ).order_by(EncryptionKey.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def rotate_key(
    db: AsyncSession,
    key_uuid: UUID,
    organization_id: int,
) -> Tuple[EncryptionKey, EncryptionKey, Optional[str]]:
    """
    Rotate an existing key.

    1. Mark old key as ROTATED
    2. Create new key of same type
    3. Link new key to old key

    Returns (old_key, new_key, new_private_key_hex_or_none)
    """
    old_key = await get_key_by_uuid(db, key_uuid, organization_id)
    if not old_key:
        raise ValueError("Key not found")
    if old_key.status != KeyStatus.ACTIVE:
        raise ValueError("Can only rotate active keys")

    old_key.status = KeyStatus.ROTATED
    old_key.rotation_date = datetime.now(timezone.utc)

    new_key, private_key_hex = await create_key(
        db, organization_id,
        key_type=old_key.key_type.value,
        algorithm=old_key.algorithm,
        label=f"Rotated from {old_key.label or str(old_key.uuid)}",
    )
    new_key.rotated_from_id = old_key.id

    await db.flush()
    logger.info(f"Rotated key {old_key.uuid} → {new_key.uuid}")
    return old_key, new_key, private_key_hex


async def revoke_key(
    db: AsyncSession,
    key_uuid: UUID,
    organization_id: int,
) -> EncryptionKey:
    """Revoke an encryption key."""
    key = await get_key_by_uuid(db, key_uuid, organization_id)
    if not key:
        raise ValueError("Key not found")
    if key.status == KeyStatus.REVOKED:
        raise ValueError("Key is already revoked")

    key.status = KeyStatus.REVOKED
    await db.flush()
    logger.info(f"Revoked key: {key.uuid}")
    return key


def get_decrypted_private_key(key: EncryptionKey) -> str:
    """Decrypt and return the private key hex for an ECC key."""
    if not key.encrypted_private_key:
        raise ValueError("No private key stored for this key")
    decrypted_bytes = decrypt_private_key(key.encrypted_private_key)
    return decrypted_bytes.hex()
