"""
CipherLink — Files API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.api.deps import get_current_user, get_current_organization
from app.db.database import get_db
from app.models.models import EncryptedFile, Organization, User, AuditEventType
from app.schemas.schemas import ApiResponse, FileResponse
from app.services.audit_service import create_audit_log
from app.storage.local import LocalStorageProvider

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("", response_model=ApiResponse, summary="List encrypted files")
async def list_files(
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EncryptedFile).where(EncryptedFile.organization_id == org.id)
        .order_by(EncryptedFile.created_at.desc()).limit(100)
    )
    files = result.scalars().all()
    return ApiResponse(success=True, data=[
        FileResponse(uuid=f.uuid, original_filename=f.original_filename,
            mime_type=f.mime_type, original_size=f.original_size,
            encrypted_size=f.encrypted_size, strategy=f.strategy.value,
            algorithm=f.algorithm, is_chunked=f.is_chunked,
            storage_provider=f.storage_provider_type.value,
            created_at=f.created_at).model_dump(mode="json")
        for f in files
    ])


@router.get("/{file_uuid}", response_model=ApiResponse, summary="Get file details")
async def get_file(
    file_uuid: UUID,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EncryptedFile).where(
        EncryptedFile.uuid == file_uuid, EncryptedFile.organization_id == org.id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(404, "File not found")
    return ApiResponse(success=True, data=FileResponse(
        uuid=f.uuid, original_filename=f.original_filename,
        mime_type=f.mime_type, original_size=f.original_size,
        encrypted_size=f.encrypted_size, strategy=f.strategy.value,
        algorithm=f.algorithm, is_chunked=f.is_chunked,
        storage_provider=f.storage_provider_type.value,
        created_at=f.created_at).model_dump(mode="json"))


@router.delete("/{file_uuid}", response_model=ApiResponse, summary="Delete encrypted file")
async def delete_file(
    file_uuid: UUID, request: Request,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EncryptedFile).where(
        EncryptedFile.uuid == file_uuid, EncryptedFile.organization_id == org.id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(404, "File not found")

    storage = LocalStorageProvider()
    await storage.delete(f.storage_path)
    await storage.delete(f"{f.storage_path}.key")

    await create_audit_log(db, AuditEventType.FILE_DELETED, org.id, user.id,
        resource_id=str(f.uuid), resource_type="encrypted_file",
        ip_address=request.client.host if request.client else None)
    await db.delete(f)
    return ApiResponse(success=True, data={"message": "File deleted"})
