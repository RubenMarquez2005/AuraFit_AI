#!/bin/bash
# Wrapper para ejecutar start-all desde frontend

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

exec "$PROJECT_ROOT/start-all.sh" "$@"
