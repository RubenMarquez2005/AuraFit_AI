#!/bin/bash
# Wrapper para ejecutar stop-all desde frontend

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

exec "$PROJECT_ROOT/stop-all.sh" "$@"
