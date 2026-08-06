#!/bin/sh
set -e

# Corre como root al arrancar el contenedor -- necesario porque el volumen
# persistente de Railway (montado en runtime, ver DATABASE_URL en
# app/core/database.py) llega con ownership de root, sin relacion con el
# chown de /app que se hizo en build-time (ver TECH_DEBT.md #9). Sin este
# paso, appuser no puede escribir el sqlite y cada INSERT/UPDATE falla con
# "attempt to write a readonly database".
DB_PATH=$(python3 -c "
import os
url = os.getenv('DATABASE_URL', 'sqlite:///./astrea.db')
print(url.removeprefix('sqlite:///') if url.startswith('sqlite:///') else '')
")

if [ -n "$DB_PATH" ]; then
    DB_DIR=$(dirname "$DB_PATH")
    mkdir -p "$DB_DIR"
    chown -R appuser:appuser "$DB_DIR"
fi

exec gosu appuser "$@"
