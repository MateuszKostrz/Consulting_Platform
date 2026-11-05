#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$REPO_ROOT/venv/bin/activate" ]; then
  source "$REPO_ROOT/venv/bin/activate"
elif [ -f "/home/ubuntu/Consulting_Platform/venv/bin/activate" ]; then
  source "/home/ubuntu/Consulting_Platform/venv/bin/activate"
fi

cd "$SCRIPT_DIR"
python sync_brevo_lists.py "$@"
