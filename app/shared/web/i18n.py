"""Internacionalización de la interfaz: catálogo de textos por idioma (web/i18n/<idioma>.json).

El SRS exige la interfaz en español (RNF-USA-05): el único idioma activo es es-PE, con fechas y horas en la zona
America/Lima (RN-34). El sistema está preparado para otro idioma: basta con agregar web/i18n/<idioma>.json con las
mismas claves y añadirlo a IDIOMAS_DISPONIBLES (tests/web/test_i18n.py comprueba que las claves coincidan).

- `t("clave.anidada", nombre=valor)` devuelve el texto con la interpolación {nombre} resuelta.
- Las claves bajo `js.` se envían al navegador (`catalogo_js`), donde las usa `Banca.t`.
"""
import json
from functools import lru_cache
from pathlib import Path

DIRECTORIO = Path(__file__).resolve().parents[3] / "web" / "i18n"
IDIOMA_ACTIVO = "es-PE"
IDIOMAS_DISPONIBLES = ("es-PE",)
ZONA_HORARIA = "America/Lima"


def _aplanar(nodo: dict, prefijo: str = "") -> dict[str, str]:
    plano: dict[str, str] = {}
    for clave, valor in nodo.items():
        if clave.startswith("_"):
            continue
        ruta = f"{prefijo}{clave}"
        if isinstance(valor, dict):
            plano.update(_aplanar(valor, ruta + "."))
        else:
            plano[ruta] = str(valor)
    return plano


@lru_cache(maxsize=len(IDIOMAS_DISPONIBLES))
def catalogo(idioma: str = IDIOMA_ACTIVO) -> dict[str, str]:
    if idioma not in IDIOMAS_DISPONIBLES:
        raise ValueError(f"Idioma no disponible: {idioma}")
    return _aplanar(json.loads((DIRECTORIO / f"{idioma}.json").read_text(encoding="utf-8")))


def t(clave: str, idioma: str = IDIOMA_ACTIVO, **parametros) -> str:
    """Texto de la clave en el idioma activo. Una clave inexistente es un error de programación: KeyError."""
    texto = catalogo(idioma)[clave]
    for nombre, valor in parametros.items():
        texto = texto.replace("{" + nombre + "}", str(valor))
    return texto


@lru_cache(maxsize=len(IDIOMAS_DISPONIBLES))
def catalogo_js(idioma: str = IDIOMA_ACTIVO) -> dict[str, str]:
    """Subcatálogo que se envía al navegador: claves `js.*` sin el prefijo."""
    return {clave[3:]: texto for clave, texto in catalogo(idioma).items() if clave.startswith("js.")}
