#!/bin/bash
set -e

echo "=== Starting CipherLink Services ==="

# 1. Start PostgreSQL service
echo "--> Starting PostgreSQL service..."
service postgresql start

# Wait for PostgreSQL to accept connections
until su - postgres -c "pg_isready"; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# 2. Configure Database & Schema
echo "--> Setting up PostgreSQL database and schema..."
su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'postgres';\"" || true
su - postgres -c "psql -c \"CREATE SCHEMA IF NOT EXISTS chat;\"" || true

# 3. Start Redis service
echo "--> Starting Redis service..."
service redis-server start || redis-server --daemonize yes

# 4. Run Alembic Database Migrations
echo "--> Running Alembic migrations..."
cd /app/backend
python -m alembic upgrade head

# 5. Start FastAPI Backend Server
echo "--> Starting FastAPI Backend on 127.0.0.1:8000..."
uvicorn src.main:app --host 127.0.0.1 --port 8000 &

# Wait for FastAPI to start
sleep 3

# 6. Start Nginx Server (Foreground process)
echo "--> Starting Nginx Web Server..."
nginx -g 'daemon off;'
