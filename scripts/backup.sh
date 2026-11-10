#!/usr/bin/env bash
# Respaldo de La Banca desplegada con docker compose (SRS v2.0, cambio 6.1).
#
# Crea UN paquete fechado:  respaldos/la-banca-AAAAMMDD-HHMMSSZ.tar.gz  con
#   mongo.archive.gz   volcado comprimido de la base (mongodump --archive --gzip)
#   archivos/          copia del bucket de MinIO (imágenes, fotos de perfil y documentos)
#   MANIFIESTO.txt     versión de la app, fecha, base, bucket, conteos por colección y número de archivos
# y borra los paquetes con más de RETENCION_RESPALDOS_DIAS días (máximo 7: RNF-PRI-02, el contenido reportado
# debe desaparecer de las copias antes de cumplir 7 días).
#
# Uso (desde la raíz del proyecto, con el compose levantado):
#   scripts/backup.sh
# Variables opcionales:
#   DIR_RESPALDOS=respaldos   RETENCION_RESPALDOS_DIAS=7
#   COMPOSE="docker compose"  (p. ej. "docker compose -p otro --env-file otro.env")
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash en Windows: no convertir rutas de los contenedores

cd "$(dirname "$0")/.."
COMPOSE=${COMPOSE:-docker compose}
DESTINO=${DIR_RESPALDOS:-respaldos}
DIAS=${RETENCION_RESPALDOS_DIAS:-7}
if [ "$DIAS" -gt 7 ]; then
  echo "RETENCION_RESPALDOS_DIAS no puede superar 7 (RNF-PRI-02)" >&2
  exit 1
fi

# Valor de una variable de la app (la que ve el contenedor: .env + valores del compose)
variable_app() { $COMPOSE exec -T app printenv "$1" 2>/dev/null | tr -d '\r' || true; }

BASE=$(variable_app MONGO_DB); BASE=${BASE:-la_banca_db}
BUCKET=$(variable_app STORAGE_BUCKET); BUCKET=${BUCKET:-la-banca}
VERSION_APP=$(cat VERSION 2>/dev/null || echo "desconocida")
FECHA=$(date -u +%Y%m%d-%H%M%SZ)
NOMBRE="la-banca-$FECHA"
mkdir -p "$DESTINO"
TMP=$(mktemp -d "$DESTINO/.tmp.XXXXXX")  # ruta relativa: sirve igual al docker de Linux y de Windows
trap 'rm -rf "$TMP"; $COMPOSE exec -T minio rm -rf "/tmp/$NOMBRE" >/dev/null 2>&1 || true' EXIT
mkdir -p "$TMP/$NOMBRE"

echo "1/3 Base de datos «$BASE» (mongodump)…"
$COMPOSE exec -T mongo mongodump --quiet --db="$BASE" --archive --gzip > "$TMP/$NOMBRE/mongo.archive.gz"
CONTEOS=$($COMPOSE exec -T mongo mongosh --quiet "$BASE" --eval \
  'db.getCollectionNames().sort().forEach(c => print(c + "=" + db.getCollection(c).countDocuments()))' | tr -d '\r')

echo "2/3 Archivos del bucket «$BUCKET» (MinIO)…"
$COMPOSE exec -T minio sh -c \
  'MC_HOST_local="http://$MINIO_ROOT_USER:$MINIO_ROOT_PASSWORD@127.0.0.1:9000" mc mirror --quiet "local/$0" "/tmp/$1" >/dev/null' \
  "$BUCKET" "$NOMBRE"
$COMPOSE exec -T minio mkdir -p "/tmp/$NOMBRE"  # bucket vacío: carpeta vacía
$COMPOSE cp "minio:/tmp/$NOMBRE" "$TMP/$NOMBRE/archivos" >/dev/null 2>&1
ARCHIVOS=$(find "$TMP/$NOMBRE/archivos" -type f | wc -l | tr -d ' ')

{
  echo "formato=la-banca-respaldo/1"
  echo "version_app=$VERSION_APP"
  echo "fecha_utc=$FECHA"
  echo "base=$BASE"
  echo "bucket=$BUCKET"
  echo "archivos=$ARCHIVOS"
  echo "$CONTEOS" | sed 's/^/coleccion./'
} > "$TMP/$NOMBRE/MANIFIESTO.txt"

echo "3/3 Paquete…"
tar -czf "$DESTINO/$NOMBRE.tar.gz" -C "$TMP" "$NOMBRE"
find "$DESTINO" -maxdepth 1 -name 'la-banca-*.tar.gz' -mtime +"$DIAS" -print -delete | sed 's/^/Rotado: /'

echo "Respaldo listo: $DESTINO/$NOMBRE.tar.gz ($ARCHIVOS archivos)"
