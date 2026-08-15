# CipherLink — Security Policy

## Encryption Standards

- **Symmetric Encryption**: AES-256-GCM (authenticated encryption)
- **Asymmetric Key Wrapping**: ECC secp256k1 via ECIES
- **Key Derivation**: CSPRNG via `os.urandom()` / `secrets` module
- **Nonces**: Unique 96-bit random nonce per encryption operation (never reused)

## Key Storage

- Private keys are **never stored as plaintext** in the database
- Private keys are encrypted at rest using the `ENCRYPTION_MASTER_KEY` (AES-256-GCM)
- For production: migrate to **AWS KMS** or equivalent HSM-backed key management
- Client secrets are stored as **SHA-256 hashes** — originals are never persisted

## Authentication

- User passwords hashed with **bcrypt**
- JWT access tokens (short-lived: 30 minutes)
- JWT refresh tokens (7 days, stored as hashes, revocable)
- OAuth2 Client Credentials flow for application authentication
- Brute-force protection (account lockout after 10 failed attempts)

## Authorization

- **RBAC**: Owner, Admin, Member, Viewer roles
- **Scope-based**: Application tokens receive only authorized scopes
- **Tenant isolation**: All database queries are scoped to `organization_id`
- Cross-tenant access is impossible by design

## Data Protection

- Encryption metadata never contains plaintext key material
- API responses never expose private keys, AES keys, passwords, or storage credentials
- Storage provider credentials are encrypted before database storage
- Request IDs (`X-Request-ID`) for tracing without exposing sensitive data

## Transport Security

- HTTPS required (TLS 1.2+)
- HSTS headers enforced
- CORS restricted to configured origins
- Security headers: X-Frame-Options, X-Content-Type-Options, CSP

## Rate Limiting

- Authentication: 10 requests/minute/IP
- API: 100 requests/minute/application
- Encryption: 50 requests/minute

## Audit Trail

- All security-sensitive events are logged
- Logs include: timestamp, organization, user, application, event type, IP, status
- Logs never contain plaintext cryptographic material

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:
- Email: security@cipherlink.example.com
- Do NOT open public issues for security vulnerabilities
