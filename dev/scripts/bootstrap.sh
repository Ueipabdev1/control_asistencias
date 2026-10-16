#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

docker compose -f compose.dev.yaml build app
docker compose -f compose.dev.yaml up -d --wait db
docker compose -f compose.dev.yaml run --rm --no-deps app python -m dev.reset_dev
docker compose -f compose.dev.yaml run --rm test
docker compose -f compose.dev.yaml up -d app

echo "Development app: http://127.0.0.1:${DEV_APP_PORT:-5017}"
echo "Synthetic admin: admin@dev.test / dev-only"
