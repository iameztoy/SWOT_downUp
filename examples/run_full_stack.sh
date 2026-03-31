#!/usr/bin/env bash
set -euo pipefail

# 1) API backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2) Frontend (run in another terminal)
# cd frontend && npm install && npm run dev
