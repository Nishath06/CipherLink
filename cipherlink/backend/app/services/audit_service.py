"""
CipherLink — Audit Service

Records security-sensitive events for compliance and monitoring.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog, AuditEventType

logger = logging.getLogger(__name__)


async def create_audit_log(
    db: AsyncSession,
    event_type: AuditEventType,
    organization_id: Optional[int] = None,
    user_id: Optional[int] = None,
    application_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> AuditLog:
    """Create an audit log entry."""
    log = AuditLog(
        event_type=event_type,
        organization_id=organization_id,
        user_id=user_id,
        application_id=application_id,
        resource_id=resource_id,
        resource_type=resource_type,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        details=details,
        request_id=request_id,
    )
    db.add(log)
    await db.flush()
    logger.info(f"Audit: {event_type.value} | org={organization_id} | status={status}")
    return log
