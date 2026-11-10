#!/usr/bin/env bash
# Restauración de La Banca desplegada con docker compose (SRS v2.0, cambio 6.1).
#
# Acepta:
#   - un paquete de scripts/backup.sh:          respaldos/la-banca-AAAAMMDD-HHMMSSZ.tar.gz
#   - un respaldo de la v1 (solo base de datos): <base>-AAAAMMDDTHHMMSSZ.archive.gz
#     (el que generan scripts/respaldo_mongodb.py y el workflow de GitHub; si está cifrado, primero:
#      gpg --decrypt archivo.archive.gz.gpg > archivo.archive.gz)
#
# REEMPLAZA los datos actuales: la base se borra y se restaura, y el bucket queda igual al del paquete.
# Detiene la app y las tareas mientras restaura; al volver a levantarla, la app aplica sola las migraciones
# pendientes (p. ej. la 001 convierte los datos de v1 a v2).
#
# Uso:
#   scripts/restore.sh respaldos/la-banca-….tar.gz [--si]      (--si: sin pedir confirmación)
# Variable opcional: COMPOSE="docker compose" (p. ej. "docker compose -p otro --env-file otro.env")
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash en Windows: no convertir rutas de los contenedores

cd "$(dirname "$0")/.."
COMPOSE=${COMPOSE:-docker compose}
PAQUETE=${1:?Uso: scripts/restore.sh <paquete.tar.gz | respaldo-v1.archive.gz> [--si]}
CONFIRMADO=${2:-}
[ -f "$PAQUETE" ] || { echo "No existe: $PAQUETE" >&2; exit 1; }

variable_app() { $COMPOSE exec -T app printenv "$1" 2>/dev/null | tr -d '\r' || true; }
$COMPOSE up -d --wait mongo minio app >/dev/null
BASE=$(variable_app MONGO_DB); BASE=${BASE:-la_banca_db}
BUCKET=$(variable_app STORAGE_BUCKET); BUCKET=${BUCKET:-la-banca}

TMP=$(mktemp -d ./.restauracion.XXXXXX)  # ruta relativa: sirve igual al docker de Linux y de Windows
trap 'rm -rf "$TMP"; $COMPOSE exec -T minio rm -rf /tmp/restauracion >/dev/null 2>&1 || true' EXIT

case "$PAQUETE" in
  *.tar.gz)
    tar -xzf "$PAQUETE" -C "$TMP"
    DIR=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    [ -f "$DIR/MANIFIESTO.txt" ] && [ -f "$DIR/mongo.archive.gz" ] || { echo "Paquete inválido: falta el manifiesto o el volcado" >&2; exit 1; }
    ARCHIVO="$DIR/mongo.archive.gz"
    ORIGEN=$(sed -n 's/^base=//p' "$DIR/MANIFIESTO.txt" | tr -d '\r')
    ARCHIVOS_DIR="$DIR/archivos"
    echo "Paquete de la versión $(sed -n 's/^version_app=//p' "$DIR/MANIFIESTO.txt") del $(sed -n 's/^fecha_utc=//p' "$DIR/MANIFIESTO.txt")"
    ;;
  *.archive.gz)
    ARCHIVO="$PAQUETE"
    # <base>-AAAAMMDDTHHMMSSZ.archive.gz (formato de la v1)
    ORIGEN=$(basename "$PAQUETE" | sed -E 's/-[0-9]{8}T[0-9]{6}Z\.archive\.gz$//; s/\.archive\.gz$//')
    ARCHIVOS_DIR=""
    echo "Respaldo de la v1 (solo base de datos; los archivos siguen en el almacenamiento de origen)"
    ;;
  *.gpg) echo "Descífralo primero: gpg --decrypt \"$PAQUETE\" > \"${PAQUETE%.gpg}\"" >&2; exit 1 ;;
  *) echo "Formato no reconocido: $PAQUETE" >&2; exit 1 ;;
esac

if [ "$CONFIRMADO" != "--si" ]; then
  read -r -p "Se REEMPLAZARÁN la base «$BASE» y el bucket «$BUCKET». ¿Continuar? (escribe si): " RESPUESTA
  [ "$RESPUESTA" = "si" ] || { echo "Cancelado"; exit 1; }
fi

echo "1/4 Deteniendo la app y las tareas…"
$COMPOSE stop app tareas >/dev/null

echo "2/4 Base de datos: $ORIGEN → $BASE (se reemplaza completa)…"
# Se borra la base entera, no solo las colecciones del volcado: un respaldo de la v1 no trae schema_migrations,
# y el registro de la base actual haría creer que la migración 001 ya se aplicó a esos datos
$COMPOSE exec -T mongo mongosh --quiet "$BASE" --eval 'db.dropDatabase()' >/dev/null
$COMPOSE exec -T mongo mongorestore --quiet --drop --archive --gzip \
  --nsInclude="$ORIGEN.*" --nsFrom="$ORIGEN.*" --nsTo="$BASE.*" < "$ARCHIVO"

if [ -n "$ARCHIVOS_DIR" ]; then
  echo "3/4 Archivos → bucket «$BUCKET»…"
  mkdir -p "$ARCHIVOS_DIR"
  $COMPOSE exec -T minio rm -rf /tmp/restauracion
  $COMPOSE cp "$ARCHIVOS_DIR" minio:/tmp/restauracion >/dev/null 2>&1
  $COMPOSE exec -T minio sh -c \
    'export MC_HOST_local="http://$MINIO_ROOT_USER:$MINIO_ROOT_PASSWORD@127.0.0.1:9000";
     mc mb --ignore-existing "local/$0" >/dev/null && mc mirror --quiet --overwrite --remove /tmp/restauracion "local/$0" >/dev/null' \
    "$BUCKET"
else
  echo "3/4 (sin archivos en un respaldo de la v1)"
fi

echo "4/4 Levantando la app (aplica las migraciones pendientes)…"
$COMPOSE up -d --wait app >/dev/null
$COMPOSE up -d tareas >/dev/null
$COMPOSE exec -T app python -m scripts.migrar --estado
echo "Restauración terminada."
