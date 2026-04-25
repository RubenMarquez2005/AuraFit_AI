#!/bin/sh
set -eu

cd /app

# Por defecto NO reentrena en cada arranque para reducir tiempo sin servicio.
# Si quieres forzar entrenamiento: RASA_SKIP_TRAIN=false.
if [ "${RASA_SKIP_TRAIN:-true}" != "true" ]; then
  echo "Entrenando modelo RASA..."
  rasa train --data data --domain domain.yml --config config.yml --out models --force
elif ! ls models/*.tar.gz >/dev/null 2>&1; then
  echo "RASA_SKIP_TRAIN=true pero no hay modelos. Entrenando de todas formas..."
  rasa train --data data --domain domain.yml --config config.yml --out models --force
fi

LATEST_MODEL="$(ls -t models/*.tar.gz | head -n 1)"
echo "Iniciando RASA con modelo: ${LATEST_MODEL}"

exec rasa run --model "$LATEST_MODEL" --enable-api --cors "*" --port 5005
