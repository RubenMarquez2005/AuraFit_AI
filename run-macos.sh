#!/bin/bash
# Script para ejecutar AuraFit AI Frontend en macOS

echo "🍎 AuraFit AI - Frontend (macOS Desktop)"
echo "========================================="
echo ""

# Ir al directorio del frontend
cd "$(dirname "$0")/frontend" || exit 1

# Verificar que Flutter está instalado
if ! command -v flutter &> /dev/null; then
    echo "❌ Flutter no está instalado"
    echo "Instálalo desde: https://flutter.dev/docs/get-started/install"
    exit 1
fi

# Obtener dependencias
echo "📦 Descargando dependencias..."
flutter pub get

# Ejecutar en macOS
echo "🖥️  Iniciando en macOS..."
flutter run -d macos

