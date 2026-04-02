#!/bin/bash
# Script maestro para ejecutar toda la aplicación AuraFit AI

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     🌟 AuraFit AI - Todo en Uno 🌟     ║"
echo "╚════════════════════════════════════════╝"
echo ""

PROJECT_ROOT="$(dirname "$0")"

# Función para mostrar menú
show_menu() {
    echo ""
    echo "Selecciona qué deseas ejecutar:"
    echo ""
    echo "1️⃣  Backend (FastAPI en http://localhost:8001)"
    echo "2️⃣  RASA IA (en http://localhost:5005)"
    echo "3️⃣  Frontend Web (en http://localhost:5000)"
    echo "4️⃣  Frontend macOS Desktop"
    echo "5️⃣  Todo (Backend + RASA + Frontend Web en ventanas separadas)"
    echo "6️⃣  Abrir documentación"
    echo "0️⃣  Salir"
    echo ""
    read -p "📌 Tu opción: " choice
}

# Función para ejecutar en terminal separada (macOS)
run_in_terminal() {
    local script=$1
    local title=$2
    
    if [ ! -f "$PROJECT_ROOT/$script" ]; then
        echo "❌ Script no encontrado: $script"
        return
    fi
    
    chmod +x "$PROJECT_ROOT/$script"
    
    # Detectar si es macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        osascript <<EOF
tell app "Terminal"
    do script "cd '$PROJECT_ROOT' && bash '$script'; exit"
    set bounds of front window to {20, 50, 800, 600}
end tell
EOF
    else
        # Para Linux, usa gnome-terminal u otra
        $PROJECT_ROOT/$script &
    fi
}

# Loop del menú
while true; do
    show_menu
    
    case $choice in
        1)
            echo "🚀 Iniciando Backend..."
            run_in_terminal "run-backend.sh" "Backend"
            ;;
        2)
            echo "🤖 Iniciando RASA..."
            run_in_terminal "run-rasa.sh" "RASA"
            ;;
        3)
            echo "🌐 Iniciando Frontend Web..."
            run_in_terminal "run-web.sh" "Frontend Web"
            ;;
        4)
            echo "🍎 Iniciando Frontend macOS..."
            run_in_terminal "run-macos.sh" "Frontend macOS"
            ;;
        5)
            echo "⚡ Iniciando TODAS las aplicaciones..."
            echo "Se abrirán en ventanas separadas..."
            sleep 1
            run_in_terminal "run-backend.sh" "Backend"
            sleep 2
            run_in_terminal "run-rasa.sh" "RASA"
            sleep 2
            echo "✅ Todo iniciado. Abre otra ventana con opción 3 para el Frontend Web"
            ;;
        6)
            echo "📖 Abriendo documentación..."
            open "$PROJECT_ROOT/docs/bitacora_tfg.md" 2>/dev/null || cat "$PROJECT_ROOT/docs/bitacora_tfg.md"
            ;;
        0)
            echo "👋 ¡Hasta pronto!"
            exit 0
            ;;
        *)
            echo "❌ Opción inválida"
            ;;
    esac
done

