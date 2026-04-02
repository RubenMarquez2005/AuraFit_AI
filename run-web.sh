#!/bin/bash
# Script para ejecutar AuraFit AI Frontend en Web

echo "🚀 AuraFit AI - Frontend (Web)"
echo "================================"
echo ""

# Ir al directorio del frontend
cd "$(dirname "$0")/frontend" || exit 1

# Verificar que Flutter está instalado
if ! command -v flutter &> /dev/null; then
    echo "❌ Flutter no está instalado"
    echo "Instálalo desde: https://flutter.dev/docs/get-started/install"
    exit 1
fi

# Limpiar caché anterior
echo "🧹 Limpiando caché..."
flutter clean

# Obtener dependencias
echo "📦 Descargando dependencias..."
flutter pub get

# Ejecutar en web
echo "🌐 Iniciando en navegador..."
flutter run -d web

