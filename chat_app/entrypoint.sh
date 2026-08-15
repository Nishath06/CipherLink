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
su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'postgres';\""  || true

# Allow password-based authentication for local TCP connections
PG_HBA=$(su - postgres -c "psql -t -c 'SHOW hba_file;'" | xargs)
if [ -f "$PG_HBA" ]; then
  # Replace peer/scram-sha-256 with md5 for local connections
  sed -i 's/^\(local\s\+all\s\+all\s\+\)peer/\1md5/' "$PG_HBA"
  sed -i 's/^\(host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+\)scram-sha-256/\1md5/' "$PG_HBA"
  sed -i 's/^\(host\s\+all\s\+all\s\+::1\/128\s\+\)scram-sha-256/\1md5/' "$PG_HBA"
  # Reload PostgreSQL to pick up pg_hba.conf changes
  su - postgres -c "psql -c 'SELECT pg_reload_conf();'" || service postgresql reload || true
fi

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
