"""
CipherLink — Usage Analytics API Routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_organization
from app.db.database import get_db
from app.models.models import (
    Application, EncryptedFile, EncryptionOperation, ApiUsage,
    Organization, User, EncryptionStrategyEnum,
)
from app.schemas.schemas import ApiResponse

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("", response_model=ApiResponse, summary="Get usage statistics")
async def get_usage(
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    # Total applications
    apps_count = (await db.execute(
        select(func.count()).select_from(Application).where(Application.organization_id == org.id)
    )).scalar() or 0

    # Total encryption operations
    ops_count = (await db.execute(
        select(func.count()).select_from(EncryptionOperation).where(EncryptionOperation.organization_id == org.id)
    )).scalar() or 0

    # Total files encrypted
    files_count = (await db.execute(
        select(func.count()).select_from(EncryptedFile).where(EncryptedFile.organization_id == org.id)
    )).scalar() or 0

    # Total storage used
    storage_used = (await db.execute(
        select(func.coalesce(func.sum(EncryptedFile.encrypted_size), 0))
        .where(EncryptedFile.organization_id == org.id)
    )).scalar() or 0

    # Failed operations
    failed_count = (await db.execute(
        select(func.count()).select_from(EncryptionOperation)
        .where(EncryptionOperation.organization_id == org.id, EncryptionOperation.status == "failed")
    )).scalar() or 0

    # Strategy distribution
    strategy_dist = {}
    for strategy in EncryptionStrategyEnum:
        count = (await db.execute(
            select(func.count()).select_from(EncryptedFile)
            .where(EncryptedFile.organization_id == org.id, EncryptedFile.strategy == strategy)
        )).scalar() or 0
        strategy_dist[strategy.value] = count

    # Recent operations
    recent_ops = (await db.execute(
        select(EncryptionOperation)
        .where(EncryptionOperation.organization_id == org.id)
        .order_by(EncryptionOperation.created_at.desc())
        .limit(10)
    )).scalars().all()

    return ApiResponse(success=True, data={
        "total_applications": apps_count,
        "total_encryption_operations": ops_count,
        "total_files_encrypted": files_count,
        "total_storage_used_bytes": storage_used,
        "total_api_requests": ops_count,
        "total_failed_requests": failed_count,
        "encryption_strategy_distribution": strategy_dist,
        "recent_operations": [
            {"uuid": str(op.uuid), "type": op.operation_type,
             "strategy": op.strategy.value if op.strategy else None,
             "status": op.status, "file_size": op.file_size,
             "duration_ms": op.duration_ms, "created_at": str(op.created_at)}
            for op in recent_ops
        ],
    })
