# 🛠️ CipherLink Encrypted Chat Application — Comprehensive Utility & Operations Guide

This document provides complete instructions for running, operating, configuring, and developing the **CipherLink Encrypted Chat Application** located inside `chat_app/`.

---

## 📁 Directory Structure

```text
chat_app/
├── backend/                  # FastAPI Python Backend
│   ├── src/
│   │   ├── main.py           # FastAPI Application Entrypoint
│   │   ├── config.py         # App Configuration & Settings
│   │   ├── database.py       # Async SQLAlchemy Database Engine & Redis
│   │   ├── models.py         # Database Models (chat schema)
│   │   ├── routers.py        # API Router aggregator
│   │   ├── authentication/   # Auth logic (JWT)
│   │   ├── chat/             # Chat messaging logic
│   │   └── websocket/        # Real-time WebSocket handlers & Adaptive Encryption
│   ├── alembic/              # Database Migrations
│   ├── tests/                # Pytest unit & integration test suite
│   ├── env/                  # Python Virtual Environment
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Vue 3 + Vite Frontend
│   ├── src/
│   │   ├── views/            # Vue Pages (Chat UI, Auth)
│   │   ├── store/            # Pinia Stores (WebSocket, Auth)
│   │   └── main.js           # Vue Application Entrypoint
│   ├── package.json          # Node.js dependencies & scripts
│   └── vite.config.js        # Vite build & dev server config
├── Dockerfile                # Production Multi-Stage Dockerfile
├── docker-compose.yml        # Docker Compose configuration
├── nginx.conf                # Nginx proxy configuration
├── entrypoint.sh             # Container startup script
├── DOCKER_GUIDE.md           # Docker deployment guide
├── cipherlink_complete_guide.md # Adaptive encryption developer guide
└── README.md                 # Primary project documentation
```

---

## ⚡ Quick Start: Local Development

### 1. Requirements
* **Python**: 3.11+
* **Node.js**: v18+ & npm
* **PostgreSQL 15**: Listening on port `5432` (Schema: `chat`)
* **Redis**: Listening on port `6379`

---

### 2. Running Backend (FastAPI)

```powershell
# Navigate to backend folder
cd chat_app/backend

# Activate virtual environment
.\env\Scripts\Activate.ps1

# Run Uvicorn server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

* **Backend Base URL**: `http://localhost:8000`
* **Swagger OpenAPI Docs**: `http://localhost:8000/docs`

---

### 3. Running Frontend (Vue 3 + Vite)

```powershell
# Navigate to frontend folder
cd chat_app/frontend

# Install dependencies (if not installed)
npm install

# Start Vite dev server
npm run dev
```

* **Frontend UI**: `http://localhost:3000` (or `http://localhost:5173`)

---

## 🔐 Hybrid Encryption Architecture

The application uses an **Adaptive Hybrid Cryptographic Engine**:
1. **Symmetric Payload Encryption (AES-256-CFB / GCM)**: Fast symmetric encryption for file attachments and media binaries.
2. **Asymmetric Key Encapsulation (ECC secp256k1 / ECIES)**: Asymmetric Elliptic Curve Cryptography used to securely wrap and distribute the symmetric AES session keys to authorized recipients.

### Strategy Selection Thresholds

| Strategy | Trigger Condition | Mechanics |
| :--- | :--- | :--- |
| **`STANDARD`** | `< 1 MB` | Single-pass AES encryption |
| **`STREAMING`** | `1 MB to 10 MB` | 64 KB sequential chunks |
| **`PARALLEL`** | `> 10 MB` | 4 MB concurrent chunked thread pool |

---

## 🐳 Running with Docker

```bash
# Build and launch all container services
cd chat_app
docker compose up -d --build
```

Access:
* **Chat Interface**: [http://localhost](http://localhost)
* **API Documentation**: [http://localhost/docs](http://localhost/docs)

---

## 🧪 Testing & Verification

Run backend unit tests:

```powershell
cd chat_app/backend
.\env\Scripts\python.exe -m pytest tests/
```
