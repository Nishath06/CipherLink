"""
CipherLink — Application Management Service

Application registration, credential generation, and lifecycle management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    generate_client_id,
    generate_client_secret,
    hash_client_secret,
)
from app.models.models import Application

logger = logging.getLogger(__name__)


async def create_application(
    db: AsyncSession,
    organization_id: int,
    name: str,
    description: Optional[str] = None,
    environment: str = "production",
    redirect_uri: Optional[str] = None,
    allowed_origins: Optional[List[str]] = None,
    scopes: Optional[List[str]] = None,
    encryption_policy: str = "BALANCED",
) -> tuple:
    """
    Register a new application.

    Returns (application, client_secret_plaintext).
    The client_secret is only returned once — only its hash is stored.
    """
    client_id = generate_client_id()
    client_secret = generate_client_secret()
    secret_hash = hash_client_secret(client_secret)

    app = Application(
        organization_id=organization_id,
        name=name,
        description=description,
        environment=environment,
        redirect_uri=redirect_uri,
        allowed_origins=allowed_origins or [],
        client_id=client_id,
        client_secret_hash=secret_hash,
        scopes=scopes or ["media:encrypt", "media:decrypt"],
        encryption_policy=encryption_policy,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)

    logger.info(f"Created application '{name}': client_id={client_id}, org={organization_id}")
    return app, client_secret


async def get_applications(
    db: AsyncSession,
    organization_id: int,
) -> list:
    """Get all applications for an organization."""
    result = await db.execute(
        select(Application)
        .where(Application.organization_id == organization_id)
        .order_by(Application.created_at.desc())
    )
    return result.scalars().all()


async def get_application_by_uuid(
    db: AsyncSession,
    app_uuid: UUID,
    organization_id: int,
) -> Optional[Application]:
    """Get a specific application by UUID, scoped to organization."""
    result = await db.execute(
        select(Application).where(
            Application.uuid == app_uuid,
            Application.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def get_application_by_client_id(
    db: AsyncSession,
    client_id: str,
) -> Optional[Application]:
    """Get an application by its client_id (for authentication)."""
    result = await db.execute(
        select(Application).where(Application.client_id == client_id)
    )
    return result.scalar_one_or_none()


async def update_application(
    db: AsyncSession,
    app_uuid: UUID,
    organization_id: int,
    **kwargs,
) -> Optional[Application]:
    """Update an application's configuration."""
    app = await get_application_by_uuid(db, app_uuid, organization_id)
    if not app:
        return None

    for key, value in kwargs.items():
        if value is not None and hasattr(app, key):
            setattr(app, key, value)

    await db.flush()
    await db.refresh(app)
    return app


async def rotate_application_secret(
    db: AsyncSession,
    app_uuid: UUID,
    organization_id: int,
) -> tuple:
    """
    Rotate an application's client secret.
    Returns (application, new_client_secret).
    """
    app = await get_application_by_uuid(db, app_uuid, organization_id)
    if not app:
        raise ValueError("Application not found")

    new_secret = generate_client_secret()
    app.client_secret_hash = hash_client_secret(new_secret)
    await db.flush()

    logger.info(f"Rotated secret for application: {app.uuid}")
    return app, new_secret


async def revoke_application(
    db: AsyncSession,
    app_uuid: UUID,
    organization_id: int,
) -> Optional[Application]:
    """Revoke (deactivate) an application."""
    app = await get_application_by_uuid(db, app_uuid, organization_id)
    if not app:
        return None

    app.is_active = False
    await db.flush()
    logger.info(f"Revoked application: {app.uuid}")
    return app


async def delete_application(
    db: AsyncSession,
    app_uuid: UUID,
    organization_id: int,
) -> bool:
    """Delete an application."""
    app = await get_application_by_uuid(db, app_uuid, organization_id)
    if not app:
        return False

    await db.delete(app)
    await db.flush()
    logger.info(f"Deleted application: {app_uuid}")
    return True
