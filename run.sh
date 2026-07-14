#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# ── Fast local development mode ────────────────────────────────────
# This runs the app directly with uvicorn (no Docker build overhead).
# Requires PostgreSQL on localhost:5432 (or set DATABASE_URL in .env).

[ -f .env ] || cp .env.example .env

# Ensure dependencies are installed
if [ ! -f venv/bin/python ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt

echo "Starting GigaCorp at http://localhost:8000"
./venv/bin/python backend/main.py
