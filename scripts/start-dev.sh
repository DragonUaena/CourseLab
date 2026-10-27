#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "$root/.venv/bin/python" ]]; then
  echo "Create .venv and install the backend first." >&2
  exit 1
fi
if [[ ! -d "$root/frontend/node_modules" ]]; then
  echo "Run npm install in frontend first." >&2
  exit 1
fi
[[ -f "$root/.env" ]] || cp "$root/.env.example" "$root/.env"

cleanup() {
  kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$root" && "$root/.venv/bin/python" -m uvicorn app.main:app --reload) &
backend_pid=$!
(cd "$root/frontend" && npm run dev) &
frontend_pid=$!

wait "$backend_pid" "$frontend_pid"

