"""Versión de La Banca: se lee del archivo VERSION de la raíz (Semantic Versioning, p. ej. «2.0.0-dev»)."""
from pathlib import Path

ARCHIVO = Path(__file__).resolve().parents[2] / "VERSION"


def leer_version() -> str:
    try:
        return ARCHIVO.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


VERSION = leer_version()
