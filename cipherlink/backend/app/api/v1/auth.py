"""
CipherLink — Authentication API Routes

Handles user registration, login, token refresh, and OAuth2 client credentials.
"""

import hashlib
import logging
import re
import traceback
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_client_secret,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.models import (
    Application,
    AuditEventType,
    Organization,
    RefreshToken,
    User,
    UserRole,
)
from app.schemas.schemas import (
    ApiResponse,
    ApplicationTokenResponse,
    ClientCredentialsRequest,
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit_service import create_audit_log
from app.api.deps import get_current_user

logger = logging.getLogger("cipherlink.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _slugify(text: str) -> str:
    """Create a URL-safe slug from text."""
    slug = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[-\s]+", "-", slug)


@router.post(
    "/register",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and user",
    description="Creates a new organization and the first admin user. "
                "The user becomes the owner of the organization.",
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"[REGISTER] ▶ Starting registration for email={body.email}, org={body.organization_name}, username={body.username}")

    try:
        # Step 1: Check if email already exists
        logger.info("[REGISTER] Step 1: Checking if email already exists...")
        existing = await db.execute(
            select(User).where(User.email == body.email)
        )
        if existing.scalar_one_or_none():
            logger.warning(f"[REGISTER] ✗ Email already registered: {body.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        logger.info("[REGISTER] Step 1: ✓ Email is available")

        # Step 2: Create organization
        logger.info(f"[REGISTER] Step 2: Creating organization '{body.organization_name}'...")
        slug = _slugify(body.organization_name)
        existing_org = await db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        if existing_org.scalar_one_or_none():
            slug = f"{slug}-{hashlib.md5(body.email.encode()).hexdigest()[:6]}"
            logger.info(f"[REGISTER] Step 2: Slug collision, using: {slug}")

        org = Organization(
            name=body.organization_name,
            slug=slug,
        )
        db.add(org)
        await db.flush()
        logger.info(f"[REGISTER] Step 2: ✓ Organization created (id={org.id}, uuid={org.uuid}, slug={slug})")

        # Step 3: Create user
        logger.info(f"[REGISTER] Step 3: Creating user '{body.username}'...")
        hashed_pw = hash_password(body.password)
        logger.info(f"[REGISTER] Step 3: Password hashed successfully")

        user = User(
            organization_id=org.id,
            email=body.email,
            username=body.username,
            hashed_password=hashed_pw,
            full_name=body.full_name,
            role=UserRole.OWNER,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        await db.refresh(org)
        logger.info(f"[REGISTER] Step 3: ✓ User created (id={user.id}, uuid={user.uuid})")

        # Step 3b: Auto-generate default ECC Key Pair for Organization
        logger.info("[REGISTER] Step 3b: Auto-generating default ECC keypair...")
        from app.services.key_management import create_key
        auto_key, _ = await create_key(
            db,
            organization_id=org.id,
            key_type="ecc",
            algorithm="secp256k1",
            label=f"Default {org.name} KeyPair"
        )
        logger.info(f"[REGISTER] Step 3b: ✓ Default ECC keypair generated (uuid={auto_key.uuid})")

        # Step 4: Audit log
        logger.info("[REGISTER] Step 4: Creating audit log...")
        await create_audit_log(
            db,
            event_type=AuditEventType.USER_REGISTER,
            organization_id=org.id,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            details={"email": body.email, "organization": body.organization_name},
        )
        logger.info("[REGISTER] Step 4: ✓ Audit log created")

        # Step 5: Generate tokens
        logger.info("[REGISTER] Step 5: Generating JWT tokens...")
        access_token = create_access_token({"sub": str(user.uuid), "org": str(org.uuid), "role": user.role.value})
        refresh_token = create_refresh_token({"sub": str(user.uuid)})
        logger.info("[REGISTER] Step 5: ✓ Tokens generated")

        # Step 6: Store refresh token hash
        logger.info("[REGISTER] Step 6: Storing refresh token hash...")
        exp_timestamp = decode_token(refresh_token)["exp"]
        expires_at_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        rt = RefreshToken(
            token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=expires_at_dt,
        )
        db.add(rt)
        logger.info("[REGISTER] Step 6: ✓ Refresh token stored")

        # Step 7: Build response
        logger.info("[REGISTER] Step 7: Building response...")
        response = ApiResponse(
            success=True,
            data={
                "user": UserResponse(
                    uuid=user.uuid,
                    email=user.email,
                    username=user.username,
                    full_name=user.full_name,
                    role=user.role.value,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    organization_uuid=org.uuid,
                    organization_name=org.name,
                    created_at=user.created_at,
                ).model_dump(mode="json"),
                "tokens": TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=30 * 60,
                ).model_dump(),
            },
        )
        logger.info(f"[REGISTER] ✅ Registration complete for {body.email}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REGISTER] ❌ Unexpected error during registration: {type(e).__name__}: {e}")
        logger.error(f"[REGISTER] ❌ Traceback:\n{traceback.format_exc()}")
        raise


@router.post(
    "/login",
    response_model=ApiResponse,
    summary="Login with email and password",
)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        # Audit failed login
        if user:
            user.failed_login_attempts += 1
            await create_audit_log(
                db,
                event_type=AuditEventType.AUTHENTICATION_FAILED,
                organization_id=user.organization_id,
                user_id=user.id,
                ip_address=request.client.host if request.client else None,
                status="failed",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Brute force protection
    if user.failed_login_attempts >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account locked due to too many failed attempts. Contact support.",
        )

    # Reset failed attempts
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)

    # Get organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = org_result.scalar_one()

    # Generate tokens
    access_token = create_access_token({"sub": str(user.uuid), "org": str(org.uuid), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.uuid)})

    exp_timestamp = decode_token(refresh_token)["exp"]
    expires_at_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    rt = RefreshToken(
        token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=expires_at_dt,
    )
    db.add(rt)

    # Audit
    await create_audit_log(
        db,
        event_type=AuditEventType.USER_LOGIN,
        organization_id=org.id,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse(
        success=True,
        data={
            "user": UserResponse(
                uuid=user.uuid,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                role=user.role.value,
                is_active=user.is_active,
                is_verified=user.is_verified,
                organization_uuid=org.uuid,
                organization_name=org.name,
                created_at=user.created_at,
            ).model_dump(mode="json"),
            "tokens": TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=30 * 60,
            ).model_dump(),
        },
    )


@router.post("/google", response_model=ApiResponse, summary="Authenticate with Google OAuth2")
@router.post("/google/", response_model=ApiResponse, summary="Authenticate with Google OAuth2 (slash)")
@router.post("/google-login", response_model=ApiResponse, summary="Authenticate with Google OAuth2 (legacy)")
@router.post("/google-login/", response_model=ApiResponse, summary="Authenticate with Google OAuth2 (legacy slash)")
async def google_login(
    request: Request,
    body: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    credential = body.credential or body.token
    email = body.email
    full_name = body.full_name or "Google User"

    # Step 1: Verify Google token (ID token or Access token)
    if credential and credential.startswith("eyJ"):
        try:
            import urllib.request
            import json
            req_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
            req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    token_info = json.loads(resp.read().decode('utf-8'))
                    email = token_info.get("email") or email
                    full_name = token_info.get("name") or full_name
        except Exception as e:
            logger.warning(f"[GOOGLE AUTH] ID Token verification check fallback: {e}")
    elif credential:
        try:
            import urllib.request
            import json
            req_url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={credential}"
            req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0", "Authorization": f"Bearer {credential}"})
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    user_info = json.loads(resp.read().decode('utf-8'))
                    email = user_info.get("email") or email
                    full_name = user_info.get("name") or user_info.get("given_name") or full_name
        except Exception as e:
            logger.warning(f"[GOOGLE AUTH] Access Token userinfo check fallback: {e}")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authentication token or valid email is required.",
        )

    # Step 2: Find existing user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create Organization & User for first-time Google sign-in
        org_name = f"{full_name.split()[0]}'s Organization" if full_name else "Google Organization"
        slug = _slugify(org_name)
        existing_org = await db.execute(select(Organization).where(Organization.slug == slug))
        if existing_org.scalar_one_or_none():
            slug = f"{slug}-{hashlib.md5(email.encode()).hexdigest()[:6]}"

        org = Organization(name=org_name, slug=slug)
        db.add(org)
        await db.flush()

        clean_username = email.split("@")[0].replace(".", "_") + "_" + hashlib.md5(email.encode()).hexdigest()[:4]
        random_pw = hash_password(uuid.uuid4().hex)

        user = User(
            organization_id=org.id,
            email=email,
            username=clean_username,
            hashed_password=random_pw,
            full_name=full_name,
            role=UserRole.OWNER,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        await db.refresh(org)

        # Auto-generate default ECC Key Pair for Organization
        from app.services.key_management import create_key
        await create_key(
            db,
            organization_id=org.id,
            key_type="ecc",
            algorithm="secp256k1",
            label=f"Default {org.name} KeyPair",
        )
    else:
        org_result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
        org = org_result.scalar_one()

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    # Update login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    user.failed_login_attempts = 0

    # Generate JWT tokens
    access_token = create_access_token({"sub": str(user.uuid), "org": str(org.uuid), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.uuid)})

    exp_timestamp = decode_token(refresh_token)["exp"]
    expires_at_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    rt = RefreshToken(
        token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=expires_at_dt,
    )
    db.add(rt)

    await create_audit_log(
        db,
        event_type=AuditEventType.USER_LOGIN,
        organization_id=org.id,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        details={"provider": "google", "email": email},
    )

    return ApiResponse(
        success=True,
        data={
            "user": UserResponse(
                uuid=user.uuid,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                role=user.role.value,
                is_active=user.is_active,
                is_verified=user.is_verified,
                organization_uuid=org.uuid,
                organization_name=org.name,
                created_at=user.created_at,
            ).model_dump(mode="json"),
            "tokens": TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=30 * 60,
            ).model_dump(),
        },
    )


@router.post(
    "/refresh",
    response_model=ApiResponse,
    summary="Refresh access token",
)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Verify refresh token exists and is not revoked
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or not found",
        )

    user_uuid = payload.get("sub")
    user_result = await db.execute(select(User).where(User.uuid == user_uuid))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = org_result.scalar_one()

    new_access = create_access_token({"sub": str(user.uuid), "org": str(org.uuid), "role": user.role.value})

    return ApiResponse(
        success=True,
        data=TokenResponse(
            access_token=new_access,
            refresh_token=body.refresh_token,
            expires_in=30 * 60,
        ).model_dump(),
    )


@router.post(
    "/token",
    response_model=ApiResponse,
    summary="OAuth2 Client Credentials — Application Token",
    description="External applications authenticate using client_id and client_secret "
                "to obtain a short-lived access token with scoped permissions.",
)
async def client_credentials_token(
    request: Request,
    body: ClientCredentialsRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application).where(Application.client_id == body.client_id)
    )
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    # Verify secret hash
    provided_hash = hash_client_secret(body.client_secret)
    if provided_hash != app.client_secret_hash:
        await create_audit_log(
            db,
            event_type=AuditEventType.AUTHENTICATION_FAILED,
            organization_id=app.organization_id,
            application_id=app.id,
            ip_address=request.client.host if request.client else None,
            status="failed",
            details={"reason": "invalid_client_secret"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    if not app.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Application is revoked",
        )

    # Determine granted scopes
    requested_scopes = body.scopes or app.scopes
    granted_scopes = [s for s in requested_scopes if s in app.scopes]

    # Create application access token
    access_token = create_access_token({
        "type": "application",
        "client_id": app.client_id,
        "org_id": str(app.organization_id),
        "scopes": granted_scopes,
    })

    return ApiResponse(
        success=True,
        data=ApplicationTokenResponse(
            access_token=access_token,
            expires_in=30 * 60,
            scopes=granted_scopes,
        ).model_dump(),
    )


@router.get(
    "/me",
    response_model=ApiResponse,
    summary="Get current authenticated user",
)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = org_result.scalar_one()

    return ApiResponse(
        success=True,
        data=UserResponse(
            uuid=user.uuid,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            organization_uuid=org.uuid,
            organization_name=org.name,
            created_at=user.created_at,
        ).model_dump(mode="json"),
    )
