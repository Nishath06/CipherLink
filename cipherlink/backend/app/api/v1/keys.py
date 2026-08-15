"""
CipherLink — Keys API Routes

Encryption key management: creation, listing, rotation, and revocation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_organization
from app.db.database import get_db
from app.models.models import AuditEventType, Organization, User
from app.schemas.schemas import (
    ApiResponse,
    KeyCreateRequest,
    KeyCreatedResponse,
    KeyResponse,
    KeyRotateResponse,
)
from app.services.key_management import (
    create_key,
    get_keys,
    get_key_by_uuid,
    rotate_key,
    revoke_key,
)
from app.services.audit_service import create_audit_log

router = APIRouter(prefix="/keys", tags=["Key Management"])


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new encryption key",
    description="Generate a new ECC or AES key. For ECC keys, the private key is shown once.",
)
async def create_new_key(
    request: Request,
    body: KeyCreateRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    if body.key_type != "ecc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ECC key pairs are supported."
        )

    existing_keys = await get_keys(db, org.id, key_type="ecc", status="active")
    if existing_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active ECC key pair already exists. You cannot create another key pair until you delete/revoke the existing one."
        )

    key, private_key_hex = await create_key(
        db, org.id, body.key_type, body.algorithm, body.label
    )

    await create_audit_log(
        db,
        event_type=AuditEventType.KEY_CREATED,
        organization_id=org.id,
        user_id=user.id,
        resource_id=str(key.uuid),
        resource_type="encryption_key",
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse(
        success=True,
        data=KeyCreatedResponse(
            uuid=key.uuid,
            key_type=key.key_type.value,
            algorithm=key.algorithm,
            status=key.status.value,
            public_key_hex=key.public_key_hex,
            label=key.label,
            rotation_date=key.rotation_date,
            created_at=key.created_at,
            private_key_hex=private_key_hex,
        ).model_dump(mode="json"),
    )


@router.get(
    "",
    response_model=ApiResponse,
    summary="List all encryption keys",
)
async def list_keys(
    key_type: str = None,
    key_status: str = None,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    keys = await get_keys(db, org.id, key_type=key_type, status=key_status)
    return ApiResponse(
        success=True,
        data=[
            KeyResponse(
                uuid=k.uuid,
                key_type=k.key_type.value,
                algorithm=k.algorithm,
                status=k.status.value,
                public_key_hex=k.public_key_hex,
                label=k.label,
                rotation_date=k.rotation_date,
                created_at=k.created_at,
            ).model_dump(mode="json")
            for k in keys
        ],
    )


@router.get(
    "/{key_uuid}",
    response_model=ApiResponse,
    summary="Get key details",
)
async def get_key_detail(
    key_uuid: UUID,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    key = await get_key_by_uuid(db, key_uuid, org.id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    return ApiResponse(
        success=True,
        data=KeyResponse(
            uuid=key.uuid,
            key_type=key.key_type.value,
            algorithm=key.algorithm,
            status=key.status.value,
            public_key_hex=key.public_key_hex,
            label=key.label,
            rotation_date=key.rotation_date,
            created_at=key.created_at,
        ).model_dump(mode="json"),
    )


@router.post(
    "/{key_uuid}/rotate",
    response_model=ApiResponse,
    summary="Rotate an encryption key",
)
async def rotate_existing_key(
    key_uuid: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    try:
        old_key, new_key, private_key_hex = await rotate_key(db, key_uuid, org.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await create_audit_log(
        db,
        event_type=AuditEventType.KEY_ROTATED,
        organization_id=org.id,
        user_id=user.id,
        resource_id=str(old_key.uuid),
        resource_type="encryption_key",
        ip_address=request.client.host if request.client else None,
        details={"new_key_uuid": str(new_key.uuid)},
    )

    return ApiResponse(
        success=True,
        data=KeyRotateResponse(
            old_key_uuid=old_key.uuid,
            new_key=KeyResponse(
                uuid=new_key.uuid,
                key_type=new_key.key_type.value,
                algorithm=new_key.algorithm,
                status=new_key.status.value,
                public_key_hex=new_key.public_key_hex,
                label=new_key.label,
                rotation_date=new_key.rotation_date,
                created_at=new_key.created_at,
            ),
        ).model_dump(mode="json"),
    )


@router.post(
    "/{key_uuid}/revoke",
    response_model=ApiResponse,
    summary="Revoke an encryption key",
)
async def revoke_existing_key(
    key_uuid: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    try:
        key = await revoke_key(db, key_uuid, org.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await create_audit_log(
        db,
        event_type=AuditEventType.KEY_REVOKED,
        organization_id=org.id,
        user_id=user.id,
        resource_id=str(key.uuid),
        resource_type="encryption_key",
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse(success=True, data={"message": "Key revoked", "key_uuid": str(key.uuid)})
