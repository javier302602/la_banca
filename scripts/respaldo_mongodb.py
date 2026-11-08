"""Respaldo de la base de La Banca con mongodump y rotación de 7 días (Entregable 2 §8.1, PA-37, RNF-PRI-02).

Uso:
    python scripts/respaldo_mongodb.py [--destino DIR] [--dias-retencion N]

Variables de entorno:
    MONGO_URI  (obligatoria)   cadena de conexión, p. ej. mongodb+srv://usuario:clave@cluster/...
    MONGO_DB   (opcional)      base a respaldar; por defecto la_banca_db
    RESPALDO_DIR (opcional)    directorio de destino; por defecto ./respaldos

Cada ejecución crea `<destino>/<base>-AAAAMMDDTHHMMSSZ.archive.gz` (mongodump --gzip --archive) y luego
elimina los respaldos de esa base con más de N días (por defecto 7). N no puede superar 7: el contenido
reportado debe desaparecer de las copias de respaldo antes de que estas cumplan 7 días (RNF-PRI-02).

La URI se pasa a mongodump en un archivo de configuración temporal (--config), no en la línea de comandos,
para que las credenciales no aparezcan en la lista de procesos ni en los registros.
Requiere MongoDB Database Tools (mongodump) en el PATH.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

RETENCION_MAXIMA_DIAS = 7
FORMATO_FECHA = "%Y%m%dT%H%M%SZ"


class ErrorRespaldo(RuntimeError):
    pass


def nombre_archivo(base: str, instante: datetime) -> str:
    return f"{base}-{instante.astimezone(timezone.utc).strftime(FORMATO_FECHA)}.archive.gz"


def fecha_de(nombre: str, base: str) -> datetime | None:
    """Instante de un archivo de respaldo de `base`, o None si el nombre no corresponde a ese patrón."""
    m = re.fullmatch(re.escape(base) + r"-(\d{8}T\d{6}Z)\.archive\.gz", nombre)
    return datetime.strptime(m.group(1), FORMATO_FECHA).replace(tzinfo=timezone.utc) if m else None


def comando_mongodump(config: Path, base: str, archivo: Path) -> list[str]:
    return ["mongodump", f"--config={config}", f"--db={base}", "--gzip", f"--archive={archivo}"]


def rotar(destino: Path, base: str, ahora: datetime, dias: int) -> list[Path]:
    """Elimina los respaldos de `base` con más de `dias` días. Devuelve los archivos eliminados."""
    limite = ahora - timedelta(days=dias)
    eliminados = []
    for archivo in sorted(destino.glob(f"{base}-*.archive.gz")):
        fecha = fecha_de(archivo.name, base)
        if fecha is not None and fecha < limite:
            archivo.unlink()
            eliminados.append(archivo)
    return eliminados


def respaldar(uri: str, base: str, destino: Path, ahora: datetime, dias: int,
              ejecutar: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> tuple[Path, list[Path]]:
    if not uri:
        raise ErrorRespaldo("Falta MONGO_URI")
    if not 1 <= dias <= RETENCION_MAXIMA_DIAS:
        raise ErrorRespaldo(f"La retención debe estar entre 1 y {RETENCION_MAXIMA_DIAS} días (RNF-PRI-02)")
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / nombre_archivo(base, ahora)
    descriptor, ruta_config = tempfile.mkstemp(prefix="mongodump-", suffix=".yaml")
    config = Path(ruta_config)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:  # mkstemp crea el archivo con permisos 0600
            f.write(f"uri: '{uri.replace(chr(39), chr(39) * 2)}'\n")
        resultado = ejecutar(comando_mongodump(config, base, archivo), capture_output=True, text=True)
    finally:
        config.unlink(missing_ok=True)
    if resultado.returncode != 0:
        archivo.unlink(missing_ok=True)  # sin respaldos a medias
        detalle = (resultado.stderr or "").replace(uri, "<MONGO_URI>").strip()
        raise ErrorRespaldo(f"mongodump terminó con código {resultado.returncode}: {detalle}")
    # Solo se rota después de un respaldo correcto: nunca se queda sin copias por un fallo
    return archivo, rotar(destino, base, ahora, dias)


def main(argv: list[str] | None = None, ejecutar=subprocess.run, ahora: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description="Respaldo de MongoDB con rotación (máx. 7 días).")
    parser.add_argument("--destino", default=os.environ.get("RESPALDO_DIR", "respaldos"))
    parser.add_argument("--dias-retencion", type=int, default=RETENCION_MAXIMA_DIAS)
    args = parser.parse_args(argv)
    try:
        archivo, eliminados = respaldar(os.environ.get("MONGO_URI", ""), os.environ.get("MONGO_DB", "la_banca_db"),
                                        Path(args.destino), ahora or datetime.now(timezone.utc),
                                        args.dias_retencion, ejecutar)
    except (ErrorRespaldo, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Respaldo creado: {archivo}")
    for viejo in eliminados:
        print(f"Respaldo eliminado por rotación: {viejo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
