#!/usr/bin/env bash
# Launcher: starts the backend (which serves the frontend) and opens the browser.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

python3 backend/server.py &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT INT TERM

for _ in {1..40}; do
  if curl -fs http://127.0.0.1:5175/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

xdg-open "http://127.0.0.1:5175/" >/dev/null 2>&1 || true

wait $SERVER_PID
