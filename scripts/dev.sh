#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

BACKEND_HEALTH_URL="http://127.0.0.1:8000/api/health"
if curl --fail --silent --show-error --max-time 3 "$BACKEND_HEALTH_URL" >/dev/null 2>&1; then
  echo "Port 8000 already has a responding ContextLoop backend. Stop it before starting a new development stack." >&2
  exit 1
fi

uv run uvicorn backend.contextloop.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

BACKEND_STARTUP_DEADLINE=$((SECONDS + 60))

echo "Waiting for the ContextLoop backend at $BACKEND_HEALTH_URL..."
while true; do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    BACKEND_EXIT_STATUS=0
    wait "$BACKEND_PID" >/dev/null 2>&1 || BACKEND_EXIT_STATUS=$?
    BACKEND_PID=""
    echo "ContextLoop backend exited before it became ready (status $BACKEND_EXIT_STATUS)." >&2
    exit 1
  fi

  if curl --fail --silent --show-error --max-time 3 "$BACKEND_HEALTH_URL" >/dev/null 2>&1; then
    sleep 0.25
    if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      echo "ContextLoop backend is ready."
      break
    fi
  fi

  if (( SECONDS >= BACKEND_STARTUP_DEADLINE )); then
    echo "Timed out after 60 seconds waiting for the ContextLoop backend." >&2
    exit 1
  fi

  sleep 0.25
done

npm --prefix frontend run dev -- --host 127.0.0.1 --strictPort
