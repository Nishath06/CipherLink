"""
CipherLink — Audit Log API Routes
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_organization
from app.db.database import get_db
from app.models.models import AuditLog, Organization, User
from app.schemas.schemas import ApiResponse, AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=ApiResponse, summary="Get audit logs")
async def get_audit_logs(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    event_type: str = None,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).where(AuditLog.organization_id == org.id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    count_q = select(func.count()).select_from(AuditLog).where(AuditLog.organization_id == org.id)
    total = (await db.execute(count_q)).scalar()

    return ApiResponse(success=True, data={
        "total": total,
        "logs": [AuditLogResponse(
            uuid=l.uuid, event_type=l.event_type.value, resource_id=l.resource_id,
            resource_type=l.resource_type, ip_address=l.ip_address,
            status=l.status, details=l.details, created_at=l.created_at,
        ).model_dump(mode="json") for l in logs],
    })
