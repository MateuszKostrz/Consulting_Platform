#!/bin/bash
# Refresh TRISO in Postgres, then rebuild Brevo lists 39, 40, and 41 only.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/platform_edu/.env}"

resolve_python() {
  for candidate in \
    "$REPO_ROOT/platform_edu/env/bin/python" \
    "$REPO_ROOT/env/bin/python" \
    "$REPO_ROOT/venv/bin/python" \
    "/home/ubuntu/Consulting_Platform/platform_edu/env/bin/python" \
    "/home/ubuntu/Consulting_Platform/venv/bin/python"
  do
    if [ -x "$candidate" ] && "$candidate" -c "import pandas" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if ! PYTHON="$(resolve_python)"; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: no Python with pandas found." >&2
  echo "  Install deps in platform_edu/env or repo venv, e.g.:" >&2
  echo "  $REPO_ROOT/platform_edu/env/bin/pip install -r $SCRIPT_DIR/requirements.txt" >&2
  exit 1
fi

cd "$SCRIPT_DIR"

"$PYTHON" dn_triso_users.py --env-file "$ENV_FILE"
"$PYTHON" dn_sync_brevo_lists.py --env-file "$ENV_FILE" --list-id 39 --lang ""
"$PYTHON" dn_sync_brevo_lists.py --env-file "$ENV_FILE" --list-id 40 --lang ""
"$PYTHON" dn_sync_brevo_lists.py --env-file "$ENV_FILE" --list-id 41 --lang ""
