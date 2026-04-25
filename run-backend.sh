#!/bin/bash
# Script para ejecutar AuraFit AI Backend

echo "⚙️  AuraFit AI - Backend (FastAPI)"
echo "=================================="
echo ""

# Ir al directorio del backend
cd "$(dirname "$0")/backend" || exit 1

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "✅ Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "⬇️  Instalando dependencias..."
pip install -q -r requirements.txt

# Ejecutar backend
echo ""
echo "🚀 Backend corriendo en http://127.0.0.1:8001"
echo "📚 Documentación en http://127.0.0.1:8001/docs"
echo ""

# Por defecto NO usamos --reload para evitar caidas al iniciar en segundo plano.
# Si necesitas autoreload en desarrollo: AURAFIT_BACKEND_RELOAD=1 ./run-backend.sh
if [[ "${AURAFIT_BACKEND_RELOAD:-0}" == "1" ]]; then
    python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
else
    python -m uvicorn main:app --host 127.0.0.1 --port 8001
fi

