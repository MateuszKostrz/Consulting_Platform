#!/bin/bash
# Refresh TRISO in Postgres, then rebuild Brevo lists 39, 40, and 41 only.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/platform_edu/.env}"

if [ -f "$REPO_ROOT/env/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/env/bin/activate"
elif [ -f "$REPO_ROOT/venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/venv/bin/activate"
fi

PYTHON="${PYTHON:-python3}"
cd "$SCRIPT_DIR"

"$PYTHON" dn_triso_users.py --env-file "$ENV_FILE"
"$PYTHON" dn_sync_brevo_lists.py --env-file "$ENV_FILE" --list-id 39 --lang ""
"$PYTHON" dn_sync_brevo_lists.py --env-file "$ENV_FILE" --list-id 40 --lang ""
"$PYTHON" dn_sync_brevo_lists.py --env-file "$ENV_FILE" --list-id 41 --lang ""
