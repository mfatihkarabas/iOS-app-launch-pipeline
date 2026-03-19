#!/usr/bin/env zsh
# ─────────────────────────────────────────────
# iOS Software Factory – launcher
# Run this instead of `python -m ios_factory.main`
# ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$HOME/python/bin/python3"

if [[ ! -x "$PYTHON" ]]; then
  echo "❌  Python 3.11 not found at $PYTHON"
  echo "    Re-run the setup steps in README.md"
  exit 1
fi

cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR/src"

# Load .env
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

exec "$PYTHON" -m ios_factory.main
