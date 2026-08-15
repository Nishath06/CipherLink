# 🔐 Project Workspace

This workspace contains two distinct, high-performance cryptographic security projects:

---

## 📁 1. `chat_app/` — CipherLink Hybrid Encrypted Chat Application

A real-time messaging and file sharing application built with **Vue 3**, **FastAPI**, **WebSockets**, **PostgreSQL**, and **Multi-Level Hybrid ECC-AES Encryption**.

### Core Highlights
* **Real-time WebSockets**: Secure, instant messaging and presence status.
* **Hybrid Cryptography**: AES-256 binary payload encryption wrapped with ECC `secp256k1` key pairs per recipient.
* **Cloud & Storage**: Integrated with AWS S3 storage and Redis PubSub caching.

### Quick Commands
```powershell
# Backend
cd chat_app/backend
.\env\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd chat_app/frontend
npm run dev
```

📖 **Detailed Documentation**: See [`chat_app/UTILITY_GUIDE.md`](chat_app/UTILITY_GUIDE.md) and [`chat_app/README.md`](chat_app/README.md).

---

## 📁 2. `cipherlink/` — Enterprise Encryption-as-a-Service Platform

A standalone Encryption-as-a-Service (EaaS) platform providing adaptive hybrid ECC-AES encryption REST APIs, organization administration, application management, and audit logging.

### Core Highlights
* **Adaptive Strategy Engine**: Automatically switches strategies (`STANDARD`, `STREAMING`, `PARALLEL`) based on file size.
* **Organization & App Management**: API keys, OAuth2 tokens, and secret key rotation.
* **Interactive Dashboard**: Vue 3 + Vuetify dashboard for file upload, encryption, decryption, and audit logging.

### Quick Commands
```powershell
# Backend
cd cipherlink/backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd cipherlink/frontend
npx vite --port 5173
```

📖 **Detailed Documentation**: See [`cipherlink/README.md`](cipherlink/README.md) and [`cipherlink/SECURITY.md`](cipherlink/SECURITY.md).
