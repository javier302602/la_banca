"""Lista de carreras del perfil (Fase 4), leída de un archivo JSON editable: config/carreras.json.

Formato: {"carreras": ["Agronomía", "Zootecnia", ...]}. Otra ruta se indica con CARRERAS_ARCHIVO en .env.
Se lee una vez por proceso: después de editar el archivo hay que reiniciar la app.
"""
import json
from functools import lru_cache
from pathlib import Path

from app.shared.config.provider import variable

RAIZ = Path(__file__).resolve().parents[3]
ARCHIVO_POR_OMISION = RAIZ / "config" / "carreras.json"


@lru_cache(maxsize=1)
def carreras() -> tuple[str, ...]:
    ruta = Path(variable("CARRERAS_ARCHIVO") or ARCHIVO_POR_OMISION)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"No se pudo leer la lista de carreras ({ruta}): {error}") from None
    lista = datos.get("carreras") if isinstance(datos, dict) else None
    if not isinstance(lista, list) or not lista or not all(isinstance(c, str) and c.strip() for c in lista):
        raise RuntimeError(f"{ruta}: «carreras» debe ser una lista de textos no vacía")
    # sin espacios sobrantes ni repetidas, en el orden del archivo
    return tuple(dict.fromkeys(" ".join(c.split()) for c in lista))
