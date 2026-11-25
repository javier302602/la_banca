"""Fase 5 — Administradores y filtro automático de palabras ofensivas. Nada de esto está escrito en el código:

- ADMIN_EMAILS (en .env): correos institucionales de los administradores, separados por comas.
- config/palabras_ofensivas.json (editable; otra ruta con PALABRAS_OFENSIVAS_ARCHIVO): palabras o frases que
  marcan una publicación o un mensaje para revisión. No se bloquea nada: solo se crea un reporte automático.
La lista de palabras se lee una vez por proceso (reiniciar la app después de editarla).
"""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.shared.config.provider import variable

RAIZ = Path(__file__).resolve().parents[3]
PALABRAS_POR_OMISION = RAIZ / "config" / "palabras_ofensivas.json"


def correos_admin() -> set[str]:
    return {c.strip().lower() for c in (variable("ADMIN_EMAILS") or "").split(",") if c.strip()}


def es_admin(correo: str) -> bool:
    return bool(correo) and correo.strip().lower() in correos_admin()


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para que «IDIOTA» o «idióta» coincidan con «idiota»."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def _patrones() -> tuple[tuple[str, re.Pattern], ...]:
    ruta = Path(variable("PALABRAS_OFENSIVAS_ARCHIVO") or PALABRAS_POR_OMISION)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"No se pudo leer la lista de palabras ofensivas ({ruta}): {error}") from None
    lista = datos.get("palabras") if isinstance(datos, dict) else None
    if not isinstance(lista, list) or not all(isinstance(p, str) for p in lista):
        raise RuntimeError(f"{ruta}: «palabras» debe ser una lista de textos")
    palabras = dict.fromkeys(_normalizar(" ".join(p.split())) for p in lista if p.strip())
    # \b: palabra completa («tonto» marca «tonto» pero no «tontería»)
    return tuple((p, re.compile(rf"\b{re.escape(p)}\b")) for p in palabras)


def palabras_ofensivas(texto: str | None) -> list[str]:
    """Palabras de la lista que aparecen en el texto (vacía si no hay ninguna)."""
    if not texto:
        return []
    normal = _normalizar(texto)
    return [palabra for palabra, patron in _patrones() if patron.search(normal)]
