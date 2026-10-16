#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -ne 1 ]]; then
    echo "Usage: bash dev/scripts/restore_dev_dump.sh path/to/dump.sql" >&2
    exit 2
fi

DUMP_PATH="$1"
if [[ ! -s "$DUMP_PATH" ]]; then
    echo "Dump file does not exist or is empty: $DUMP_PATH" >&2
    exit 2
fi

if grep -Eiq '^[[:space:]]*(CREATE[[:space:]]+DATABASE|USE[[:space:]]+)' "$DUMP_PATH"; then
    echo "Refusing dumps containing CREATE DATABASE or USE directives" >&2
    exit 2
fi

if [[ "${CONFIRM_DEV_RESTORE:-}" != "YES" ]]; then
    read -r -p "Replace ONLY control_asistencias_dev in the development container? Type RESTORE_DEV: " confirmation
    if [[ "$confirmation" != "RESTORE_DEV" ]]; then
        echo "Restore cancelled" >&2
        exit 1
    fi
fi

docker compose -f compose.dev.yaml up -d --wait db
docker compose -f compose.dev.yaml exec -T db mariadb -uroot -pdev_root_only -e "DROP DATABASE IF EXISTS control_asistencias_dev; CREATE DATABASE control_asistencias_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
docker compose -f compose.dev.yaml exec -T db mariadb -uroot -pdev_root_only control_asistencias_dev < "$DUMP_PATH"

echo "Restored $DUMP_PATH into control_asistencias_dev only"
