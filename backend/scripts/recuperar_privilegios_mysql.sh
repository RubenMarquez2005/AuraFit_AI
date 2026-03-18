#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   ./scripts/recuperar_privilegios_mysql.sh 'Curso2026@'

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 '<nueva_password_root>'"
  exit 1
fi

MYSQL_ROOT_PASSWORD="$1"
MYSQL_BIN="/usr/local/mysql/bin/mysql"
MYSQLD_SAFE="/usr/local/mysql/bin/mysqld_safe"
MYSQL_SERVER="/usr/local/mysql/support-files/mysql.server"

echo "1) Deteniendo MySQL..."
sudo "$MYSQL_SERVER" stop || true
sudo pkill mysqld || true
sleep 2

echo "2) Iniciando MySQL en modo recuperacion..."
sudo "$MYSQLD_SAFE" --skip-grant-tables --skip-networking >/tmp/mysql-recovery.log 2>&1 &
sleep 6

echo "3) Restaurando privilegios de root y base aurafit_db..."
"$MYSQL_BIN" -u root -e "
FLUSH PRIVILEGES;
ALTER USER 'root'@'%' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
CREATE DATABASE IF NOT EXISTS aurafit_db;
GRANT ALL PRIVILEGES ON aurafit_db.* TO 'root'@'%';
FLUSH PRIVILEGES;
"

echo "4) Reiniciando MySQL en modo normal..."
sudo pkill mysqld || true
sleep 2
sudo "$MYSQL_SERVER" start
sleep 3

echo "5) Verificando acceso y permisos..."
"$MYSQL_BIN" -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW DATABASES;" | sed -n '1,30p'

echo "Recuperacion completada"
