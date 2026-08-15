"""
CipherLink — Encryption API Routes
"""

import io
import uuid as uuid_mod
import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_organization
from app.db.database import get_db
from app.models.models import (
    AuditEventType, EncryptedFile, EncryptionKey, EncryptionOperation,
    EncryptionStrategyEnum, KeyStatus, KeyType, Organization,
    StorageProviderType, User,
)
from app.schemas.schemas import ApiResponse, EncryptionMetadataResponse, EncryptionStrategyInfo
from app.services.encryption.adaptive import adaptive_encrypt, adaptive_decrypt
from app.services.key_management import get_active_ecc_key, get_decrypted_private_key
from app.services.audit_service import create_audit_log
from app.storage.local import LocalStorageProvider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/encryption", tags=["Encryption"])

STRATEGY_MAP = {
    "STANDARD_AES": EncryptionStrategyEnum.STANDARD_AES,
    "HYBRID_AES_ECC": EncryptionStrategyEnum.HYBRID_AES_ECC,
    "CHUNKED_AES": EncryptionStrategyEnum.CHUNKED_AES,
}


def _get_storage():
    return LocalStorageProvider()


@router.post("/encrypt", response_model=ApiResponse, summary="Encrypt a file")
async def encrypt_file(
    request: Request, file: UploadFile = File(...),
    key_uuid: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    file_size = len(file_bytes)
    filename = file.filename or "unknown"
    mime_type = file.content_type or "application/octet-stream"

    if key_uuid:
        res = await db.execute(select(EncryptionKey).where(
            EncryptionKey.uuid == UUID(key_uuid), EncryptionKey.organization_id == org.id,
            EncryptionKey.key_type == KeyType.ECC, EncryptionKey.status == KeyStatus.ACTIVE))
        ecc_key = res.scalar_one_or_none()
    else:
        ecc_key = await get_active_ecc_key(db, org.id)

    if not ecc_key:
        raise HTTPException(400, "No active ECC key. Create one first.")

    try:
        result = adaptive_encrypt(file_bytes, filename, mime_type, ecc_key.public_key_hex)
    except Exception as e:
        db.add(EncryptionOperation(organization_id=org.id, operation_type="encrypt",
                                   file_size=file_size, status="failed", error_message=str(e)))
        raise HTTPException(500, f"Encryption failed: {e}")

    ef_uuid = uuid_mod.uuid4()
    # Combine file metadata with file_id and user info
    result["metadata"]["file_id"] = str(ef_uuid)
    result["metadata"]["user_id"] = user.id
    result["metadata"]["user_uuid"] = str(user.uuid)

    # Package metadata header into the downloaded .enc file
    import json
    header_bytes = json.dumps(result["metadata"]).encode('utf-8')
    header_len_bytes = len(header_bytes).to_bytes(4, byteorder='big')
    # Magic prefix "CLNK" (4 bytes) + header length (4 bytes) + JSON header bytes + ciphertext
    packaged_enc_bytes = b"CLNK" + header_len_bytes + header_bytes + result["ciphertext"]

    storage = _get_storage()
    storage_key = f"encrypted/{org.id}/{uuid_mod.uuid4().hex}/{filename}.enc"
    await storage.upload(storage_key, packaged_enc_bytes)
    await storage.upload(f"{storage_key}.key", result["encrypted_aes_key"])

    ef = EncryptedFile(
        uuid=ef_uuid, organization_id=org.id, user_id=user.id, original_filename=filename, mime_type=mime_type,
        original_size=file_size, encrypted_size=len(result["ciphertext"]),
        strategy=STRATEGY_MAP.get(result["strategy"], EncryptionStrategyEnum.STANDARD_AES),
        algorithm="AES-256-GCM", key_wrap="ECC-SECP256K1",
        encryption_metadata=result["metadata"], storage_provider_type=StorageProviderType.LOCAL,
        storage_path=storage_key, encryption_key_id=ecc_key.id,
        is_chunked=result["strategy"] == "CHUNKED_AES",
        chunk_count=result["metadata"].get("chunk_count"),
        chunk_size=result["metadata"].get("chunk_size"))
    db.add(ef)
    await db.flush()
    await db.refresh(ef)

    db.add(EncryptionOperation(organization_id=org.id, operation_type="encrypt",
                               strategy=ef.strategy, file_id=ef.id, file_size=file_size,
                               duration_ms=result["duration_ms"], status="success"))
    await create_audit_log(db, AuditEventType.FILE_ENCRYPTED, org.id, user.id,
                           resource_id=str(ef.uuid), resource_type="encrypted_file",
                           ip_address=request.client.host if request.client else None,
                           details={"strategy": result["strategy"], "file_size": file_size})

    # Use the API download endpoint (handles filenames with special chars correctly)
    enc_download_url = f"/api/v1/encryption/download-encrypted/{ef.uuid}"

    return ApiResponse(success=True, data={
        "file_id": str(ef.uuid),
        "strategy": result["strategy"],
        "algorithm": "AES-256-GCM",
        "key_wrap": "ECC-SECP256K1",
        "is_chunked": ef.is_chunked,
        "chunk_count": ef.chunk_count,
        "chunk_size": ef.chunk_size,
        "original_size": file_size,
        "encrypted_size": len(result["ciphertext"]),
        "storage_provider": "local",
        "encrypted_download_url": enc_download_url,
        "created_at": str(ef.created_at),
    })


@router.get("/download-encrypted/{file_uuid}", summary="Download raw encrypted file")
async def download_encrypted_file(
    file_uuid: str,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(EncryptedFile).where(
        EncryptedFile.uuid == UUID(file_uuid), EncryptedFile.organization_id == org.id))
    ef = res.scalar_one_or_none()
    if not ef:
        raise HTTPException(404, "Encrypted file record not found")

    if ef.user_id and ef.user_id != user.id:
        raise HTTPException(403, "Access denied: You are not the owner of this encrypted file")

    storage = _get_storage()
    packaged_data = await storage.download(ef.storage_path)

    # Sanitize filename for Content-Disposition header
    safe_filename = ef.original_filename.replace('"', '_').replace(',', '_') + ".enc"

    return StreamingResponse(
        io.BytesIO(packaged_data),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Length": str(len(packaged_data)),
        }
    )


@router.post("/decrypt/{file_uuid}", response_model=ApiResponse, summary="Decrypt a file")
async def decrypt_file(
    file_uuid: str, request: Request,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(EncryptedFile).where(
        EncryptedFile.uuid == UUID(file_uuid), EncryptedFile.organization_id == org.id))
    ef = res.scalar_one_or_none()
    if not ef:
        raise HTTPException(404, "File not found")

    # Validate that logged in user is the owner of the encrypted file
    if ef.user_id and ef.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access Denied: Logged in user does not match file owner ID")

    key_res = await db.execute(select(EncryptionKey).where(EncryptionKey.id == ef.encryption_key_id))
    ecc_key = key_res.scalar_one_or_none()
    if not ecc_key:
        raise HTTPException(400, "Encryption key not found")

    storage = _get_storage()
    ciphertext = await storage.download(ef.storage_path)
    encrypted_aes_key = await storage.download(f"{ef.storage_path}.key")

    # Strip CLNK header prefix from stored ciphertext if packaged
    if ciphertext.startswith(b"CLNK") and len(ciphertext) > 8:
        try:
            header_len = int.from_bytes(ciphertext[4:8], byteorder='big')
            if len(ciphertext) >= 8 + header_len:
                ciphertext = ciphertext[8 + header_len :]
        except Exception:
            pass

    # Decrypt the AES key using user's ECC private key first, then decrypt file
    private_key_hex = get_decrypted_private_key(ecc_key)

    try:
        start = time.monotonic()
        plaintext = adaptive_decrypt(ciphertext, encrypted_aes_key, ef.encryption_metadata, private_key_hex)
        duration_ms = (time.monotonic() - start) * 1000
    except Exception as e:
        db.add(EncryptionOperation(organization_id=org.id, operation_type="decrypt",
                                   file_id=ef.id, status="failed", error_message=str(e)))
        raise HTTPException(500, f"Decryption failed: {e}")

    dl_key = f"decrypted/{org.id}/{uuid_mod.uuid4().hex}/{ef.original_filename}"
    await storage.upload(dl_key, plaintext, content_type=ef.mime_type)
    db.add(EncryptionOperation(organization_id=org.id, operation_type="decrypt",
                               strategy=ef.strategy, file_id=ef.id, file_size=ef.original_size,
                               duration_ms=duration_ms, status="success"))
    await create_audit_log(db, AuditEventType.FILE_DECRYPTED, org.id, user.id,
                           resource_id=str(ef.uuid), resource_type="encrypted_file",
                           ip_address=request.client.host if request.client else None)
    dl_url = await storage.generate_download_url(dl_key)

    return ApiResponse(success=True, data={"file_id": str(ef.uuid),
        "original_filename": ef.original_filename, "mime_type": ef.mime_type,
        "original_size": ef.original_size, "download_url": dl_url})


@router.post("/decrypt-uploaded", response_model=ApiResponse, summary="Decrypt an uploaded encrypted (.enc) file")
async def decrypt_uploaded_file(
    file: UploadFile = File(...),
    file_id: Optional[str] = Form(None),
    request: Request = None,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    import json

    uploaded_bytes = await file.read()
    raw_filename = file.filename or ""

    embedded_metadata = None
    uploaded_ciphertext = uploaded_bytes

    # STEP 1: Extract embedded metadata header from the uploaded .enc file
    if uploaded_bytes.startswith(b"CLNK") and len(uploaded_bytes) > 8:
        try:
            header_len = int.from_bytes(uploaded_bytes[4:8], byteorder='big')
            if len(uploaded_bytes) >= 8 + header_len:
                header_json_bytes = uploaded_bytes[8 : 8 + header_len]
                embedded_metadata = json.loads(header_json_bytes.decode('utf-8'))
                uploaded_ciphertext = uploaded_bytes[8 + header_len :]
                logger.info(f"[DECRYPT-UPLOADED] Extracted embedded metadata: file_id={embedded_metadata.get('file_id')}, user_id={embedded_metadata.get('user_id')}")
        except Exception as e:
            logger.warning(f"[DECRYPT-UPLOADED] Could not parse embedded .enc header: {e}")

    # STEP 2: Verify user ownership from extracted metadata first (if available)
    if embedded_metadata and embedded_metadata.get("user_id"):
        if embedded_metadata["user_id"] != user.id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Access Denied: The owner of this file (User ID: {embedded_metadata['user_id']}) does not match the logged-in user (User ID: {user.id})."
            )

    # Use file_id from metadata if available
    target_file_id = file_id or (embedded_metadata.get("file_id") if embedded_metadata else None)

    ef = None
    # STEP 3: Retrieve record from database using file_id (or fallback filename)
    if target_file_id and str(target_file_id).strip():
        try:
            target_uuid = UUID(str(target_file_id).strip())
            res = await db.execute(select(EncryptedFile).where(
                EncryptedFile.uuid == target_uuid, EncryptedFile.organization_id == org.id))
            ef = res.scalar_one_or_none()
        except Exception:
            pass

    if not ef and raw_filename:
        clean_name = raw_filename[:-4] if raw_filename.endswith(".enc") else raw_filename
        res = await db.execute(select(EncryptedFile).where(
            EncryptedFile.organization_id == org.id,
            EncryptedFile.user_id == user.id,
            EncryptedFile.original_filename == clean_name
        ).order_by(EncryptedFile.created_at.desc()))
        ef = res.scalars().first()

    if not ef:
        raise HTTPException(404, "No matching encrypted file record found for your account. Please check the File ID.")

    # Validate database owner ID as well
    if ef.user_id and ef.user_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Access Denied: Logged-in user ({user.username}) is not authorized to decrypt this file."
        )

    # Use embedded metadata if extracted from file, otherwise fall back to DB encryption_metadata
    metadata_to_use = embedded_metadata or ef.encryption_metadata

    # Validate uploaded ciphertext size matches expected encrypted size
    if ef.encrypted_size and len(uploaded_ciphertext) != ef.encrypted_size:
        logger.warning(
            f"[DECRYPT-UPLOADED] Ciphertext size mismatch: uploaded={len(uploaded_ciphertext)}B, "
            f"expected={ef.encrypted_size}B. The .enc file may be corrupted or incomplete."
        )
        raise HTTPException(
            400,
            f"Uploaded .enc file size mismatch: got {len(uploaded_ciphertext)} bytes of ciphertext, "
            f"expected {ef.encrypted_size} bytes. The file may be corrupted or incomplete. "
            f"Please re-download the .enc file and try again."
        )

    # STEP 4: Retrieve the active/associated ECC key for the organization
    key_res = await db.execute(select(EncryptionKey).where(EncryptionKey.id == ef.encryption_key_id))
    ecc_key = key_res.scalar_one_or_none()
    if not ecc_key:
        ecc_key = await get_active_ecc_key(db, org.id)
    if not ecc_key:
        raise HTTPException(400, "ECC Encryption key associated with this file not found")

    # STEP 5: Retrieve encrypted AES key from storage
    storage = _get_storage()
    encrypted_aes_key = await storage.download(f"{ef.storage_path}.key")

    # STEP 6: Decrypt AES key using user's ECC private key first, then decrypt original file
    private_key_hex = get_decrypted_private_key(ecc_key)

    try:
        start = time.monotonic()
        plaintext = adaptive_decrypt(uploaded_ciphertext, encrypted_aes_key, metadata_to_use, private_key_hex)
        duration_ms = (time.monotonic() - start) * 1000
    except Exception as e:
        import traceback
        logger.error(f"Decryption error: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(500, f"Decryption failed: {type(e).__name__}: {e}")

    dl_key = f"decrypted/{org.id}/{uuid_mod.uuid4().hex}/{ef.original_filename}"
    await storage.upload(dl_key, plaintext, content_type=ef.mime_type)

    dl_url = await storage.generate_download_url(dl_key)

    return ApiResponse(success=True, data={
        "file_id": str(ef.uuid),
        "original_filename": ef.original_filename,
        "mime_type": ef.mime_type,
        "original_size": ef.original_size,
        "download_url": dl_url
    })


@router.get("/strategies", response_model=ApiResponse, summary="List encryption strategies")
async def list_strategies():
    return ApiResponse(success=True, data=[
        {"name": "STANDARD_AES", "description": "AES-256-GCM for small files",
         "file_size_range": "< 1 MB", "algorithm": "AES-256-GCM", "key_wrap": "ECC-SECP256K1"},
        {"name": "HYBRID_AES_ECC", "description": "Hybrid AES+ECC for medium files",
         "file_size_range": "1–10 MB", "algorithm": "AES-256-GCM", "key_wrap": "ECC-SECP256K1"},
        {"name": "CHUNKED_AES", "description": "Parallel chunked encryption for large files",
         "file_size_range": "> 10 MB", "algorithm": "AES-256-GCM", "key_wrap": "ECC-SECP256K1"},
    ])
