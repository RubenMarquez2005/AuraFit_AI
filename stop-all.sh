#!/bin/bash
# Script para detener todos los servicios AuraFit AI

echo "🛑 Deteniendo todos los servicios AuraFit AI..."
echo ""

# Matar procesos en puertos específicos
echo "🔌 Buscando procesos en puertos..."

# Backend (puerto 8001)
if lsof -ti tcp:8001 >/dev/null 2>&1; then
    echo "  - Deteniendo Backend (puerto 8001)..."
    lsof -ti tcp:8001 | xargs -r kill -9 2>/dev/null
    sleep 1
fi

# RASA (puerto 5005)
if lsof -ti tcp:5005 >/dev/null 2>&1; then
    echo "  - Deteniendo RASA (puerto 5005)..."
    lsof -ti tcp:5005 | xargs -r kill -9 2>/dev/null
    sleep 1
fi

# Frontend Web (puerto 3000)
if lsof -ti tcp:3000 >/dev/null 2>&1; then
    echo "  - Deteniendo Frontend Web (puerto 3000)..."
    for pid in $(lsof -ti tcp:3000); do
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
fi

# Frontend Web alternativo (puerto 5000) - VS Code
if lsof -ti tcp:5000 >/dev/null 2>&1; then
    echo "  - Deteniendo procesos en puerto 5000..."
    for pid in $(lsof -ti tcp:5000); do
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 2
fi

# Matar procesos Node.js (frontend web)
if pgrep -f "npm.*start" >/dev/null; then
    echo "  - Deteniendo procesos npm..."
    pkill -f "npm.*start" 2>/dev/null || true
    sleep 1
fi

# Matar procesos Flutter (si está corriendo)
if pgrep -f "flutter run" >/dev/null; then
    echo "  - Deteniendo Flutter..."
    pkill -f "flutter run" 2>/dev/null || true
    sleep 1
fi

echo ""
echo "✅ Todos los servicios han sido detenidos"
echo ""
echo "Verificación de puertos:"
echo "  Backend (8001):     $(lsof -ti tcp:8001 >/dev/null 2>&1 && echo '❌ Aún activo' || echo '✅ Detenido')"
echo "  RASA (5005):        $(lsof -ti tcp:5005 >/dev/null 2>&1 && echo '❌ Aún activo' || echo '✅ Detenido')"
echo "  Web Frontend (3000): $(lsof -ti tcp:3000 >/dev/null 2>&1 && echo '❌ Aún activo' || echo '✅ Detenido')"
