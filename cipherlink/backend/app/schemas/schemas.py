"""
CipherLink — Pydantic Schemas

Request/response models for API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ══════════════════════════════════════════════════════════════════════════════
# GENERIC API RESPONSE
# ══════════════════════════════════════════════════════════════════════════════

class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
    request_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# AUTH SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    uuid: UUID
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    organization_uuid: UUID
    organization_name: str
    created_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class ApplicationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    environment: str = Field(default="production", pattern="^(development|staging|production)$")
    redirect_uri: Optional[str] = None
    allowed_origins: List[str] = []
    scopes: List[str] = Field(
        default=["media:encrypt", "media:decrypt"],
        description="API scopes for this application"
    )
    encryption_policy: str = Field(default="BALANCED", pattern="^(BALANCED|STRICT_SECURITY|LOW_MEMORY|HIGH_PERFORMANCE)$")


class ApplicationResponse(BaseModel):
    uuid: UUID
    name: str
    description: Optional[str]
    environment: str
    client_id: str
    scopes: List[str]
    is_active: bool
    encryption_policy: str
    created_at: datetime
    updated_at: datetime


class ApplicationCreatedResponse(ApplicationResponse):
    """Returned only on creation — includes the client_secret (shown once)."""
    client_secret: str


class ApplicationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    redirect_uri: Optional[str] = None
    allowed_origins: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    encryption_policy: Optional[str] = None


# ── Application Token (OAuth2 Client Credentials) ────────────────────────────

class ClientCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    scopes: Optional[List[str]] = None


class ApplicationTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scopes: List[str]


# ══════════════════════════════════════════════════════════════════════════════
# KEY MANAGEMENT SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class KeyCreateRequest(BaseModel):
    key_type: str = Field(..., pattern="^(ecc|aes)$")
    algorithm: str = Field(default="secp256k1")
    label: Optional[str] = Field(None, max_length=255)


class KeyResponse(BaseModel):
    uuid: UUID
    key_type: str
    algorithm: str
    status: str
    public_key_hex: Optional[str]
    label: Optional[str]
    rotation_date: Optional[datetime]
    created_at: datetime


class KeyCreatedResponse(KeyResponse):
    """On initial creation only, may include the private key hex for client-side use."""
    private_key_hex: Optional[str] = None


class KeyRotateResponse(BaseModel):
    old_key_uuid: UUID
    new_key: KeyResponse


# ══════════════════════════════════════════════════════════════════════════════
# ENCRYPTION SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class EncryptionMetadataResponse(BaseModel):
    file_id: UUID
    strategy: str
    algorithm: str
    key_wrap: Optional[str]
    is_chunked: bool
    chunk_count: Optional[int]
    chunk_size: Optional[int]
    original_size: int
    encrypted_size: int
    storage_provider: str
    created_at: datetime


class EncryptionStrategyInfo(BaseModel):
    name: str
    description: str
    file_size_range: str
    algorithm: str
    key_wrap: Optional[str]


class DecryptionResponse(BaseModel):
    file_id: UUID
    original_filename: str
    mime_type: Optional[str]
    original_size: int
    download_url: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class StorageConfigCreateRequest(BaseModel):
    provider_type: str = Field(..., pattern="^(local|aws_s3|azure_blob)$")
    name: str = Field(..., min_length=2, max_length=255)
    is_default: bool = False
    config: Dict[str, Any] = Field(
        ...,
        description="Provider-specific configuration (bucket, region, credentials, etc.)"
    )


class StorageConfigResponse(BaseModel):
    uuid: UUID
    provider_type: str
    name: str
    is_default: bool
    is_active: bool
    display_info: Dict[str, Any]
    created_at: datetime


class StorageTestResponse(BaseModel):
    success: bool
    message: str
    provider_type: str


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class AuditLogResponse(BaseModel):
    uuid: UUID
    event_type: str
    resource_id: Optional[str]
    resource_type: Optional[str]
    ip_address: Optional[str]
    status: str
    details: Optional[Dict[str, Any]]
    created_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# USAGE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class UsageSummaryResponse(BaseModel):
    total_applications: int
    total_encryption_operations: int
    total_files_encrypted: int
    total_storage_used_bytes: int
    total_api_requests: int
    total_failed_requests: int
    encryption_strategy_distribution: Dict[str, int]
    recent_operations: List[Dict[str, Any]]


# ══════════════════════════════════════════════════════════════════════════════
# FILE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class FileResponse(BaseModel):
    uuid: UUID
    original_filename: str
    mime_type: Optional[str]
    original_size: int
    encrypted_size: int
    strategy: str
    algorithm: str
    is_chunked: bool
    storage_provider: str
    created_at: datetime
