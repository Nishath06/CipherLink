# 🚀 How to Run CipherLink using Docker

This document provides a step-by-step guide to build and run the combined Docker container for **CipherLink**, which includes:
- **Frontend**: Vue 3 + Vuetify + Vite
- **Backend**: FastAPI + Uvicorn + WebSockets
- **Encryption**: Hybrid ECC (secp256k1) & AES-CFB
- **Database**: PostgreSQL 15 (Schema: `chat`)
- **Cache**: Redis
- **Web Server**: Nginx (Port 80)

---

## 📋 Prerequisites

Ensure you have installed:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) or **Docker Engine** (Linux).

---

## 🛠️ Step-by-Step Instructions

### Step 1: Open Terminal / PowerShell
Navigate to the root directory of the project:
```bash
cd /path/to/CipherLink
```

---

### Step 2: Build the Docker Image
Run the following command to build the combined image:

```bash
docker build -t cipherlink:latest .
```

*Note: The first build will take a few minutes to download packages, compile frontend assets, and set up Python dependencies.*

---

### Step 3: Run the Docker Container
Run the container in detached mode (`-d`) mapping port `80`, optionally passing your AWS S3 credentials for file attachment storage:

```bash
docker run -d \
  --name cipherlink-app \
  -p 80:80 \
  -e AWS_ACCESS_KEY_ID="your_aws_access_key" \
  -e AWS_SECRET_ACCESS_KEY="your_aws_secret_key" \
  -e AWS_REGION_NAME="us-east-1" \
  -e AWS_IMAGES_BUCKET="fastapijp" \
  cipherlink:latest
```

*Note: AWS S3 is used for storing encrypted file attachments (images, PDFs, documents).*

---

## 🐙 Alternative: Run using Docker Compose

If you prefer using **Docker Compose**:

```bash
docker compose up -d --build
```

To stop and remove the container:
```bash
docker compose down
```

---

## 🌐 Accessing the Application

Once the container is running:
- 📱 **Web Application (UI)**: [http://localhost](http://localhost)
- 📚 **Swagger API Docs**: [http://localhost/docs](http://localhost/docs)
- ⚙️ **OpenAPI Schema**: [http://localhost/openapi.json](http://localhost/openapi.json)
- 🔌 **WebSocket Connection**: `ws://localhost/ws/{chat_guid}`

---

## 🛠️ Useful Management Commands

### 1. View Logs
To view real-time logs from PostgreSQL, Redis, Alembic, FastAPI, and Nginx:
```bash
docker logs -f cipherlink-app
```

### 2. Access Container Shell
To enter the running container:
```bash
docker exec -it cipherlink-app bash
```

### 3. Check Database Tables
To inspect tables and encrypted keys inside PostgreSQL:
```bash
docker exec -it cipherlink-app su - postgres -c "psql -d postgres -c '\dt chat.*'"
```

### 4. Stop & Remove Container
```bash
docker stop cipherlink-app
docker rm cipherlink-app
```
