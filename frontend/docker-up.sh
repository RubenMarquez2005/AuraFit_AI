#!/bin/bash
# Wrapper para iniciar Docker desde frontend/

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

exec "$PROJECT_ROOT/docker-up.sh" "$@"