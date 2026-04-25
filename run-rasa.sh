#!/bin/bash
# Script para ejecutar AuraFit AI RASA

set -e

echo "🤖 AuraFit AI - RASA (NLU & IA)"
echo "================================="
echo ""

# Ir al directorio de RASA
cd "$(dirname "$0")/ai_rasa" || exit 1

# Activar virtualenv si existe
if [ -d "venv_rasa/bin" ]; then
    echo "✅ Activando entorno RASA..."
    source venv_rasa/bin/activate
else
    echo "⚠️  Virtualenv no encontrado. Asegúrate de haber ejecutado la instalación."
    exit 1
fi

# Entrenar modelo si no existe
if ! ls models/*.tar.gz >/dev/null 2>&1; then
    echo "📚 Entrenando modelo RASA (primera vez)..."
    /Users/rubenperez/Documents/AuraFit_AI/ai_rasa/venv_rasa/bin/python -m rasa train --data data --domain domain.yml --config config.yml --out models --force
fi

LATEST_MODEL="$(ls -t models/*.tar.gz | head -1)"

# Ejecutar RASA core + API
echo ""
echo "🚀 RASA corriendo en http://127.0.0.1:5005"
echo "🔌 API Webhook disponible en /webhooks/rest/webhook"
echo "🧠 Modelo cargado: $LATEST_MODEL"
echo ""

/Users/rubenperez/Documents/AuraFit_AI/ai_rasa/venv_rasa/bin/python -m rasa run --model "$LATEST_MODEL" --enable-api --cors "*" -p 5005

