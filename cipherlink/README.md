# 🔐 CipherLink — Enterprise Encryption-as-a-Service Platform

**Secure Once. Access Everywhere. Integrate Anywhere. Trust Always.**

CipherLink is a standalone encryption platform that provides adaptive hybrid ECC-AES encryption as a service. External applications register, authenticate, and use CipherLink's REST APIs to encrypt/decrypt media and manage encryption keys.

---

## Architecture

```
                 ┌───────────────────────────┐
                 │       CIPHERLINK          │
                 │ Encryption-as-a-Service   │
                 │                           │
                 │ Auth · Applications       │
                 │ Keys · Adaptive Encryption│
                 │ Storage · Audit           │
                 └─────────────┬─────────────┘
                               │
                     Secure HTTPS API
                               │
            ┌──────────────────┼─────────────────┐
            │                  │                 │
            ▼                  ▼                 ▼
      Secure Chat        Media Utility      Your App
```

## Adaptive Encryption Strategies

| File Size | Strategy | Algorithm | Key Protection |
|-----------|----------|-----------|----------------|
| < 1 MB | Standard AES | AES-256-GCM | ECC-SECP256K1 |
| 1–10 MB | Hybrid AES+ECC | AES-256-GCM | ECC-SECP256K1 |
| > 10 MB | Chunked Parallel | AES-256-GCM | ECC-SECP256K1 |

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy Async, PostgreSQL, Redis
- **Frontend**: Vue 3, Vuetify 3, Pinia, Vite
- **Crypto**: `cryptography` (AES-256-GCM), `ecies`/`coincurve` (secp256k1)
- **Infrastructure**: Docker, Nginx, AWS S3

## Quick Start

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your secrets
```

### 2. Start with Docker

```bash
docker compose up -d --build
```

### 3. Access

- **Dashboard**: http://localhost
- **API Docs**: http://localhost/docs
- **ReDoc**: http://localhost/redoc
- **API**: http://localhost/api/v1/

### 4. Register & Login

1. Open http://localhost/register
2. Create your organization
3. Login and access the dashboard

### 5. Create an Encryption Key

Dashboard → Keys → Generate Key → ECC (secp256k1)

### 6. Register an Application

Dashboard → Applications → Register Application

### 7. Encrypt a File

Dashboard → Encryption → Upload & Encrypt

---

## External Application Integration

```python
import requests

# 1. Get access token
token_resp = requests.post("http://localhost/api/v1/auth/token", json={
    "client_id": "cl_app_xxx",
    "client_secret": "cl_secret_xxx"
})
token = token_resp.json()["data"]["access_token"]

# 2. Encrypt a file
enc_resp = requests.post(
    "http://localhost/api/v1/encryption/encrypt",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": open("image.jpg", "rb")}
)
file_id = enc_resp.json()["data"]["file_id"]

# 3. Decrypt
dec_resp = requests.post(
    f"http://localhost/api/v1/encryption/decrypt/{file_id}",
    headers={"Authorization": f"Bearer {token}"}
)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register organization + user |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/token` | OAuth2 client credentials |
| POST | `/api/v1/applications` | Register application |
| GET | `/api/v1/applications` | List applications |
| POST | `/api/v1/keys` | Create encryption key |
| POST | `/api/v1/keys/{id}/rotate` | Rotate key |
| POST | `/api/v1/encryption/encrypt` | Encrypt file |
| POST | `/api/v1/encryption/decrypt/{id}` | Decrypt file |
| GET | `/api/v1/files` | List encrypted files |
| GET | `/api/v1/audit/logs` | Audit logs |
| GET | `/api/v1/usage` | Usage statistics |

## Project Structure

```
cipherlink/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── api/v1/              # API routes
│   │   ├── core/                # Config, security
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic
│   │   │   └── encryption/      # AES, ECC, hybrid, chunked, adaptive
│   │   ├── storage/             # Storage abstraction (local, S3, Azure)
│   │   └── db/                  # Database connection
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/               # Pages (landing, auth, dashboard)
│   │   ├── layouts/             # Dashboard layout
│   │   ├── stores/              # Pinia stores
│   │   ├── services/            # API client
│   │   └── router/              # Vue Router
│   └── package.json
├── nginx/nginx.conf
├── docker-compose.yml
├── .env.example
├── SECURITY.md
└── README.md
```

## Security

See [SECURITY.md](SECURITY.md) for the complete security policy.

## License

Proprietary — CipherLink Encryption Platform
 

cd e:\wd\wd\Akatsuki\cipherlink
docker compose up -d --build
