#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_FILE="$ROOT_DIR/.graphify_python"

if [[ ! -f "$PYTHON_FILE" ]]; then
  echo "Missing .graphify_python; expected a Python interpreter path." >&2
  exit 1
fi

GRAPHIFY_PYTHON="$(tr -d '\n' < "$PYTHON_FILE")"

if [[ -z "$GRAPHIFY_PYTHON" ]]; then
  echo ".graphify_python is empty." >&2
  exit 1
fi

if [[ ! -x "$GRAPHIFY_PYTHON" ]]; then
  echo "Configured graphify interpreter is not executable: $GRAPHIFY_PYTHON" >&2
  exit 1
fi

cd "$ROOT_DIR"

"$GRAPHIFY_PYTHON" -c "import graphify" >/dev/null 2>&1 || {
  echo "Configured interpreter cannot import graphify: $GRAPHIFY_PYTHON" >&2
  exit 1
}

"$GRAPHIFY_PYTHON" -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
