"""CU-16 — Consultar términos de uso y política de privacidad. Fuente del texto vigente.

El texto se versiona con el código en web/terminos/terminos.txt; no requiere MongoDB.
"""
from functools import lru_cache
from pathlib import Path

RUTA_TERMINOS = Path(__file__).resolve().parents[4] / "web" / "terminos" / "terminos.txt"


@lru_cache(maxsize=1)
def leer_terminos() -> str:
    return RUTA_TERMINOS.read_text(encoding="utf-8")
