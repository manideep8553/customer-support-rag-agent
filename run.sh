#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
[ -d venv/lib ] || python3 -m venv venv
./venv/bin/pip install -q -r requirements.txt 2>/dev/null
[ -f react-frontend/dist/index.html ] || (cd react-frontend && npm install --silent && npm run build --silent)
./venv/bin/python backend/main.py
