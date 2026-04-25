#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ] && [ -f .env.docker.example ]; then
  cp .env.docker.example .env
  echo "Se creo .env desde .env.docker.example"
fi

docker compose up --build -d

MYSQL_PORT="${MYSQL_HOST_PORT:-3307}"

echo ""
echo "AuraFit levantado con Docker:"
echo "- Frontend: http://localhost:3000"
echo "- Backend:  http://localhost:8001/docs"
echo "- RASA:     http://localhost:5005"
echo "- MySQL:    localhost:${MYSQL_PORT}"
