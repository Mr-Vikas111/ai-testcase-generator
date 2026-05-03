#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Resolve python executable in priority order:
# 1) PYTHON_BIN env override
# 2) local project venv
# 3) active shell python3/python
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "Error: Python not found. Set PYTHON_BIN or install Python." >&2
    exit 1
  fi
fi

if [[ "$#" -gt 0 ]]; then
  exec "$PYTHON_BIN" webhook_server.py "$@"
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5055}"
MODEL="${MODEL_OLLAMA:-}"

if [[ -n "$MODEL" ]]; then
  exec "$PYTHON_BIN" webhook_server.py --host "$HOST" --port "$PORT" --model "$MODEL"
fi

exec "$PYTHON_BIN" webhook_server.py --host "$HOST" --port "$PORT"
