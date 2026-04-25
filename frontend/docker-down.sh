#!/bin/bash
# Wrapper para detener Docker desde frontend/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

exec "$PROJECT_ROOT/docker-down.sh" "$@"