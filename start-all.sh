#!/bin/bash
# Lanzador único AuraFit AI: backend + RASA + web + macOS

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
RUN_WEB=true
RUN_MAC=true
USE_TERMINAL=false
LOG_DIR="$PROJECT_ROOT/.logs"
PID_DIR="$PROJECT_ROOT/.pids"

for arg in "$@"; do
  case "$arg" in
    --no-web)
      RUN_WEB=false
      ;;
    --no-mac)
      RUN_MAC=false
      ;;
    --terminal)
      USE_TERMINAL=true
      ;;
    -h|--help)
      echo "Uso: ./start-all.sh [--no-web] [--no-mac] [--terminal]"
      echo "  Por defecto: inicia en segundo plano (sin ventanas emergentes de Terminal)."
      echo "  --terminal: abre cada servicio en una ventana de Terminal (modo anterior)."
      exit 0
      ;;
    *)
      echo "Argumento no reconocido: $arg"
      echo "Usa --help para ver opciones."
      exit 1
      ;;
  esac
done

is_port_busy() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

open_in_terminal() {
  local title="$1"
  local command="$2"

  if [[ "$OSTYPE" == darwin* ]]; then
    osascript <<EOF
tell application "Terminal"
  activate
  do script "cd '$PROJECT_ROOT' && echo '▶ $title' && $command"
end tell
EOF
  else
    nohup bash -lc "cd '$PROJECT_ROOT' && $command" \
      >"$LOG_DIR/${title// /_}.log" 2>&1 &
  fi
}

run_in_background() {
  local title="$1"
  local command="$2"
  local logfile="$LOG_DIR/${title// /_}.log"
  local pidfile="$PID_DIR/${title// /_}.pid"

  nohup bash -lc "cd '$PROJECT_ROOT' && $command" >"$logfile" 2>&1 &
  echo $! >"$pidfile"
  echo "▶ $title en segundo plano (PID $(cat "$pidfile")). Log: $logfile"
}

launch_service() {
  local title="$1"
  local command="$2"

  if $USE_TERMINAL; then
    open_in_terminal "$title" "$command"
  else
    run_in_background "$title" "$command"
  fi
}

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║      AuraFit AI - Inicio con un comando      ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

mkdir -p "$LOG_DIR" "$PID_DIR"

if is_port_busy 8001; then
  echo "ℹ Backend ya está en ejecución en 127.0.0.1:8001"
else
  launch_service "Backend FastAPI" "bash ./run-backend.sh"
  sleep 2
  if ! is_port_busy 8001; then
    echo "❌ Backend no arrancó correctamente."
    echo "   Revisa log: $LOG_DIR/Backend_FastAPI.log"
  fi
fi

if is_port_busy 5005; then
  echo "ℹ RASA ya está en ejecución en 127.0.0.1:5005"
else
  launch_service "RASA" "bash ./run-rasa.sh"
  sleep 2
  if ! is_port_busy 5005; then
    echo "❌ RASA no arrancó correctamente."
    echo "   Revisa log: $LOG_DIR/RASA.log"
  fi
fi

if $RUN_WEB; then
  if is_port_busy 3000; then
    echo "ℹ Frontend web ya está escuchando en http://localhost:3000"
  else
    launch_service "Frontend Web" "bash ./run-web.sh"
    sleep 2
  fi
fi

if $RUN_MAC; then
  if command -v xcodebuild >/dev/null 2>&1; then
    launch_service "Frontend macOS" "bash ./run-macos.sh"
  else
    echo "⚠ macOS frontend omitido: Xcode Command Line Tools no instaladas (xcodebuild no disponible)."
    echo "  Instala con: xcode-select --install"
  fi
fi

echo ""
echo "✅ Inicio lanzado."
echo "   Backend: http://127.0.0.1:8001"
echo "   Docs:    http://127.0.0.1:8001/docs"
echo "   RASA:    http://127.0.0.1:5005"
if $RUN_WEB; then
  echo "   Web:     http://localhost:3000"
fi
echo ""