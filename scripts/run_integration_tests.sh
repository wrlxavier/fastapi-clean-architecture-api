#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${TEST_DATABASE_URL:-}" ]]; then
  echo "TEST_DATABASE_URL must be set to run integration tests." >&2
  exit 1
fi

cd "$ROOT_DIR"

export PYTHONPATH="app/src"
export DATABASE_URL="$TEST_DATABASE_URL"

./.venv/bin/alembic upgrade head
./.venv/bin/pytest tests/integration "$@"
