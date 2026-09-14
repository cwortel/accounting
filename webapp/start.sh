#!/usr/bin/env bash
# Starts both the FastAPI backend and Next.js frontend for local development.
# Ctrl+C stops both.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Setting up backend virtual environment..."
  python3 -m venv "$BACKEND_DIR/.venv"
  "$BACKEND_DIR/.venv/bin/python" -m pip install -q -r "$BACKEND_DIR/requirements.txt"
fi
if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "Created backend/.env — edit it to set a real ACCOUNTING_API_TOKEN."
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi
if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
  cp "$FRONTEND_DIR/.env.local.example" "$FRONTEND_DIR/.env.local"
  echo "Created frontend/.env.local — make sure BACKEND_API_KEY matches backend/.env."
fi

cleanup() {
  echo ""
  echo "Stopping backend and frontend..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend  -> http://localhost:8000"
(cd "$BACKEND_DIR" && .venv/bin/uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

echo "Starting frontend -> http://localhost:3000"
(cd "$FRONTEND_DIR" && npm run dev) &
FRONTEND_PID=$!

wait
