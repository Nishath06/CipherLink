"""
CipherLink — Database Models

Multi-tenant models for the Encryption-as-a-Service platform.
Every tenant-scoped table includes `organization_id`.
All externally visible IDs use UUIDs.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


# ── Helper ────────────────────────────────────────────────────────────────────

def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class KeyType(str, enum.Enum):
    ECC = "ecc"
    AES = "aes"


class KeyStatus(str, enum.Enum):
    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"


class StorageProviderType(str, enum.Enum):
    LOCAL = "local"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"


class EncryptionStrategyEnum(str, enum.Enum):
    STANDARD_AES = "STANDARD_AES"
    HYBRID_AES_ECC = "HYBRID_AES_ECC"
    CHUNKED_AES = "CHUNKED_AES"


class AuditEventType(str, enum.Enum):
    USER_LOGIN = "USER_LOGIN"
    USER_REGISTER = "USER_REGISTER"
    APPLICATION_CREATED = "APPLICATION_CREATED"
    APPLICATION_REVOKED = "APPLICATION_REVOKED"
    KEY_CREATED = "KEY_CREATED"
    KEY_ROTATED = "KEY_ROTATED"
    KEY_REVOKED = "KEY_REVOKED"
    FILE_ENCRYPTED = "FILE_ENCRYPTED"
    FILE_DECRYPTED = "FILE_DECRYPTED"
    FILE_DELETED = "FILE_DELETED"
    STORAGE_CONNECTED = "STORAGE_CONNECTED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    SECRET_ROTATED = "SECRET_ROTATED"


# ══════════════════════════════════════════════════════════════════════════════
# ORGANIZATION
# ══════════════════════════════════════════════════════════════════════════════

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="organization", cascade="all, delete-orphan")
    keys = relationship("EncryptionKey", back_populates="organization", cascade="all, delete-orphan")
    storage_providers = relationship("StorageConfig", back_populates="organization", cascade="all, delete-orphan")
    encrypted_files = relationship("EncryptedFile", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════════════════════════
# USER
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    email = Column(String(320), nullable=False)
    username = Column(String(150), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
        UniqueConstraint("organization_id", "username", name="uq_user_org_username"),
        Index("ix_users_org_id", "organization_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    environment = Column(String(50), default="production", nullable=False)
    redirect_uri = Column(String(2048), nullable=True)
    allowed_origins = Column(JSONB, default=list, nullable=False)

    client_id = Column(String(255), unique=True, nullable=False, index=True)
    client_secret_hash = Column(String(255), nullable=False)

    scopes = Column(JSONB, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    storage_provider_id = Column(Integer, ForeignKey("storage_configs.id"), nullable=True)
    encryption_policy = Column(String(50), default="BALANCED", nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_applications_org_id", "organization_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="applications")
    storage_config = relationship("StorageConfig", foreign_keys=[storage_provider_id])
    encryption_operations = relationship("EncryptionOperation", back_populates="application", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════════════════════════
# ENCRYPTION KEY
# ══════════════════════════════════════════════════════════════════════════════

class EncryptionKey(Base):
    __tablename__ = "encryption_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    key_type = Column(Enum(KeyType), nullable=False)
    algorithm = Column(String(50), nullable=False)  # e.g. "secp256k1", "AES-256-GCM"
    status = Column(Enum(KeyStatus), default=KeyStatus.ACTIVE, nullable=False)

    # Public key stored as hex (ECC) or metadata
    public_key_hex = Column(Text, nullable=True)

    # Private key encrypted with master key, stored as bytes
    encrypted_private_key = Column(LargeBinary, nullable=True)

    # For managed AES keys
    encrypted_key_material = Column(LargeBinary, nullable=True)

    label = Column(String(255), nullable=True)
    rotation_date = Column(DateTime(timezone=True), nullable=True)
    rotated_from_id = Column(Integer, ForeignKey("encryption_keys.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_keys_org_id", "organization_id"),
        Index("ix_keys_status", "status"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="keys")
    rotated_from = relationship("EncryptionKey", remote_side=[id])


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class StorageConfig(Base):
    __tablename__ = "storage_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    provider_type = Column(Enum(StorageProviderType), nullable=False)
    name = Column(String(255), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Encrypted configuration blob (contains bucket, region, credentials, etc.)
    encrypted_config = Column(LargeBinary, nullable=True)

    # Non-sensitive display info
    display_info = Column(JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_storage_org_id", "organization_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="storage_providers")


# ══════════════════════════════════════════════════════════════════════════════
# ENCRYPTED FILE
# ══════════════════════════════════════════════════════════════════════════════

class EncryptedFile(Base):
    __tablename__ = "encrypted_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    original_filename = Column(String(512), nullable=False)
    mime_type = Column(String(255), nullable=True)
    original_size = Column(Integer, nullable=False)
    encrypted_size = Column(Integer, nullable=False)

    strategy = Column(Enum(EncryptionStrategyEnum), nullable=False)
    algorithm = Column(String(50), default="AES-256-GCM", nullable=False)
    key_wrap = Column(String(50), nullable=True)  # e.g. "ECC-SECP256K1"

    # Encryption metadata (nonces, auth_tags, chunk info, etc.)
    encryption_metadata = Column(JSONB, nullable=False)

    # Storage location
    storage_provider_type = Column(Enum(StorageProviderType), nullable=False)
    storage_path = Column(Text, nullable=False)

    # Key references
    encryption_key_id = Column(Integer, ForeignKey("encryption_keys.id"), nullable=True)

    # Chunking info
    is_chunked = Column(Boolean, default=False, nullable=False)
    chunk_count = Column(Integer, nullable=True)
    chunk_size = Column(Integer, nullable=True)

    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_files_org_id", "organization_id"),
        Index("ix_files_app_id", "application_id"),
        Index("ix_files_user_id", "user_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="encrypted_files")
    encryption_key = relationship("EncryptionKey")
    application = relationship("Application")


# ══════════════════════════════════════════════════════════════════════════════
# ENCRYPTION OPERATION
# ══════════════════════════════════════════════════════════════════════════════

class EncryptionOperation(Base):
    __tablename__ = "encryption_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    operation_type = Column(String(20), nullable=False)  # "encrypt" or "decrypt"
    strategy = Column(Enum(EncryptionStrategyEnum), nullable=True)
    file_id = Column(Integer, ForeignKey("encrypted_files.id"), nullable=True)

    file_size = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    status = Column(String(20), default="success", nullable=False)  # "success", "failed"
    error_message = Column(Text, nullable=True)

    request_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_operations_org_id", "organization_id"),
        Index("ix_operations_created", "created_at"),
    )

    # Relationships
    application = relationship("Application", back_populates="encryption_operations")
    encrypted_file = relationship("EncryptedFile")


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=new_uuid, unique=True, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    event_type = Column(Enum(AuditEventType), nullable=False)
    resource_id = Column(String(255), nullable=True)
    resource_type = Column(String(100), nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), default="success", nullable=False)
    details = Column(JSONB, nullable=True)

    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_org_id", "organization_id"),
        Index("ix_audit_event_type", "event_type"),
        Index("ix_audit_created", "created_at"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")


# ══════════════════════════════════════════════════════════════════════════════
# REFRESH TOKEN
# ══════════════════════════════════════════════════════════════════════════════

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


# ══════════════════════════════════════════════════════════════════════════════
# API USAGE
# ══════════════════════════════════════════════════════════════════════════════

class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    endpoint = Column(String(512), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_usage_org_id", "organization_id"),
        Index("ix_usage_created", "created_at"),
    )
