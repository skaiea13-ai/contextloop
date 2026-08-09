#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
    wait "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${SESSION_URL_FILE:-}" ]]; then
    rm -f -- "$SESSION_URL_FILE"
  fi
}
trap cleanup EXIT INT TERM

LOCAL_SESSION_TOKEN="${CONTEXTLOOP_LOCAL_TOKEN:-}"
if [[ -n "$LOCAL_SESSION_TOKEN" && ${#LOCAL_SESSION_TOKEN} -lt 32 ]]; then
  echo "CONTEXTLOOP_LOCAL_TOKEN must contain at least 32 characters." >&2
  exit 1
fi
if [[ -z "$LOCAL_SESSION_TOKEN" ]]; then
  LOCAL_SESSION_TOKEN="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi
export CONTEXTLOOP_LOCAL_TOKEN="$LOCAL_SESSION_TOKEN"

BACKEND_HEALTH_URL="http://127.0.0.1:8000/api/health"
if curl --silent --max-time 3 --output /dev/null "$BACKEND_HEALTH_URL" 2>/dev/null; then
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

  if curl --fail --silent --show-error --max-time 3 \
    --header "X-ContextLoop-Token: $LOCAL_SESSION_TOKEN" \
    "$BACKEND_HEALTH_URL" >/dev/null 2>&1; then
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

npm --prefix frontend run dev -- --host 127.0.0.1 --strictPort &
FRONTEND_PID=$!
FRONTEND_URL="http://127.0.0.1:5173"
FRONTEND_STARTUP_DEADLINE=$((SECONDS + 60))

echo "Waiting for the ContextLoop frontend at $FRONTEND_URL..."
while true; do
  if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    FRONTEND_EXIT_STATUS=0
    wait "$FRONTEND_PID" >/dev/null 2>&1 || FRONTEND_EXIT_STATUS=$?
    FRONTEND_PID=""
    echo "ContextLoop frontend exited before it became ready (status $FRONTEND_EXIT_STATUS)." >&2
    exit 1
  fi

  if curl --fail --silent --show-error --max-time 3 "$FRONTEND_URL" >/dev/null 2>&1; then
    break
  fi

  if (( SECONDS >= FRONTEND_STARTUP_DEADLINE )); then
    echo "Timed out after 60 seconds waiting for the ContextLoop frontend." >&2
    exit 1
  fi

  sleep 0.25
done

SESSION_URL="${FRONTEND_URL}/#contextloop_token=${LOCAL_SESSION_TOKEN}"
if [[ "${CONTEXTLOOP_SKIP_BROWSER_OPEN:-0}" != "1" ]] && command -v open >/dev/null 2>&1; then
  echo "Opening the protected ContextLoop session in the default browser."
  open "$SESSION_URL"
elif [[ "${CONTEXTLOOP_SKIP_BROWSER_OPEN:-0}" != "1" ]] && command -v xdg-open >/dev/null 2>&1; then
  echo "Opening the protected ContextLoop session in the default browser."
  xdg-open "$SESSION_URL" >/dev/null 2>&1 &
else
  SESSION_URL_FILE="$(mktemp "${TMPDIR:-/tmp}/contextloop-session-url.XXXXXX")"
  chmod 600 "$SESSION_URL_FILE"
  printf '%s\n' "$SESSION_URL" >"$SESSION_URL_FILE"
  echo "Protected session URL saved to $SESSION_URL_FILE."
fi

wait "$FRONTEND_PID"
