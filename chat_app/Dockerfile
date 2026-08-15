# ==========================================
# Stage 1: Build Frontend (Vue 3 / Vite)
# ==========================================
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: All-in-One Application Container
# ==========================================
FROM python:3.11-slim

# Avoid prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system runtime & build dependencies (PostgreSQL, Redis, Nginx, Build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    curl \
    gcc \
    g++ \
    libffi-dev \
    libpq-dev \
    python3-dev \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Copy backend requirements and install Python packages
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir coincurve eciespy cryptography boto3

# Copy backend source code
COPY backend/ ./

# Copy built frontend assets from Stage 1 into Nginx web root
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy and setup entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose HTTP port
EXPOSE 80

# Run entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
