"""
CipherLink — Applications API Routes

Application registration, management, and credential lifecycle.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_organization
from app.db.database import get_db
from app.models.models import AuditEventType, Organization, User
from app.schemas.schemas import (
    ApiResponse,
    ApplicationCreateRequest,
    ApplicationCreatedResponse,
    ApplicationResponse,
    ApplicationUpdateRequest,
)
from app.services.application_service import (
    create_application,
    delete_application,
    get_application_by_uuid,
    get_applications,
    revoke_application,
    rotate_application_secret,
    update_application,
)
from app.services.audit_service import create_audit_log

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new application",
    description="Register an external application and receive client_id and client_secret. "
                "The client_secret is displayed only once.",
)
async def create_app(
    request: Request,
    body: ApplicationCreateRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    app, client_secret = await create_application(
        db,
        organization_id=org.id,
        name=body.name,
        description=body.description,
        environment=body.environment,
        redirect_uri=body.redirect_uri,
        allowed_origins=body.allowed_origins,
        scopes=body.scopes,
        encryption_policy=body.encryption_policy,
    )

    await create_audit_log(
        db,
        event_type=AuditEventType.APPLICATION_CREATED,
        organization_id=org.id,
        user_id=user.id,
        resource_id=str(app.uuid),
        resource_type="application",
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse(
        success=True,
        data=ApplicationCreatedResponse(
            uuid=app.uuid,
            name=app.name,
            description=app.description,
            environment=app.environment,
            client_id=app.client_id,
            client_secret=client_secret,
            scopes=app.scopes,
            is_active=app.is_active,
            encryption_policy=app.encryption_policy,
            created_at=app.created_at,
            updated_at=app.updated_at,
        ).model_dump(mode="json"),
    )


@router.get(
    "",
    response_model=ApiResponse,
    summary="List all applications",
)
async def list_apps(
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    apps = await get_applications(db, org.id)
    return ApiResponse(
        success=True,
        data=[
            ApplicationResponse(
                uuid=a.uuid,
                name=a.name,
                description=a.description,
                environment=a.environment,
                client_id=a.client_id,
                scopes=a.scopes,
                is_active=a.is_active,
                encryption_policy=a.encryption_policy,
                created_at=a.created_at,
                updated_at=a.updated_at,
            ).model_dump(mode="json")
            for a in apps
        ],
    )


@router.get(
    "/{app_uuid}",
    response_model=ApiResponse,
    summary="Get application details",
)
async def get_app(
    app_uuid: UUID,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    app = await get_application_by_uuid(db, app_uuid, org.id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return ApiResponse(
        success=True,
        data=ApplicationResponse(
            uuid=app.uuid,
            name=app.name,
            description=app.description,
            environment=app.environment,
            client_id=app.client_id,
            scopes=app.scopes,
            is_active=app.is_active,
            encryption_policy=app.encryption_policy,
            created_at=app.created_at,
            updated_at=app.updated_at,
        ).model_dump(mode="json"),
    )


@router.patch(
    "/{app_uuid}",
    response_model=ApiResponse,
    summary="Update application",
)
async def patch_app(
    app_uuid: UUID,
    body: ApplicationUpdateRequest,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    app = await update_application(
        db, app_uuid, org.id,
        **body.model_dump(exclude_unset=True),
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return ApiResponse(
        success=True,
        data=ApplicationResponse(
            uuid=app.uuid,
            name=app.name,
            description=app.description,
            environment=app.environment,
            client_id=app.client_id,
            scopes=app.scopes,
            is_active=app.is_active,
            encryption_policy=app.encryption_policy,
            created_at=app.created_at,
            updated_at=app.updated_at,
        ).model_dump(mode="json"),
    )


@router.post(
    "/{app_uuid}/rotate-secret",
    response_model=ApiResponse,
    summary="Rotate application client secret",
)
async def rotate_secret(
    app_uuid: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    try:
        app, new_secret = await rotate_application_secret(db, app_uuid, org.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await create_audit_log(
        db,
        event_type=AuditEventType.SECRET_ROTATED,
        organization_id=org.id,
        user_id=user.id,
        resource_id=str(app.uuid),
        resource_type="application",
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse(
        success=True,
        data={
            "client_id": app.client_id,
            "client_secret": new_secret,
            "message": "Secret rotated. This is the only time the new secret will be displayed.",
        },
    )


@router.post(
    "/{app_uuid}/revoke",
    response_model=ApiResponse,
    summary="Revoke an application",
)
async def revoke_app(
    app_uuid: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    app = await revoke_application(db, app_uuid, org.id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    await create_audit_log(
        db,
        event_type=AuditEventType.APPLICATION_REVOKED,
        organization_id=org.id,
        user_id=user.id,
        resource_id=str(app.uuid),
        resource_type="application",
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse(success=True, data={"message": "Application revoked"})


@router.delete(
    "/{app_uuid}",
    response_model=ApiResponse,
    summary="Delete an application",
)
async def delete_app(
    app_uuid: UUID,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_application(db, app_uuid, org.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")

    return ApiResponse(success=True, data={"message": "Application deleted"})
