"""Exporta los tokens de diseño de web/static/css/tokens.css a docs/investigacion/tokens.json.

    python scripts/exportar_tokens.py               # escribe el JSON
    python scripts/exportar_tokens.py --comprobar   # falla si el JSON no coincide con el CSS

Formato de Tokens Studio para Figma, con tres conjuntos:
- «global»: tipografía, espaciado, radios y tamaños (bloque :root, iguales en ambos modos);
- «claro»: colores y sombras del bloque :root;
- «oscuro»: colores y sombras del bloque [data-bs-theme="dark"].
Dos temas en "$themes": Claro (global + claro) y Oscuro (global + oscuro). Cada token es
{"value": ..., "type": ..., "description": ...}; las sombras son boxShadow con x, y, blur, spread y color.
En Tokens Studio: Settings → Sync (repositorio o archivo local) y elegir el tema Claro u Oscuro.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "web" / "static" / "css" / "tokens.css"
JSON = RAIZ / "docs" / "investigacion" / "tokens.json"

# prefijo de la variable → (grupo en el JSON, tipo de Tokens Studio, depende del modo)
CATEGORIAS = [
    ("color-", "color", "color", True),
    ("sombra-", "boxShadow", "boxShadow", True),
    ("fuente-familia-", "fontFamilies", "fontFamilies", False),
    ("fuente-tamano-", "fontSizes", "fontSizes", False),
    ("fuente-peso-", "fontWeights", "fontWeights", False),
    ("interlineado-", "lineHeights", "lineHeights", False),
    ("espacio-", "spacing", "spacing", False),
    ("radio-", "borderRadius", "borderRadius", False),
    ("punto-", "sizing", "sizing", False),
]
DECLARACION = re.compile(r"--lb-([a-z0-9-]+):\s*([^;]+);[ \t]*(?:/\*\s*(.*?)\s*\*/)?")
SOMBRA = re.compile(r"(-?[\d.]+(?:px)?)\s+(-?[\d.]+(?:px)?)\s+([\d.]+(?:px)?)(?:\s+(-?[\d.]+(?:px)?))?\s+(rgba?\([^)]*\)|#[0-9a-fA-F]{3,8})")


def _bloque(css: str, selector: str) -> str:
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\n\}", css, re.S)
    return m.group(1) if m else ""


def leer_css(css: str, selector: str = ":root") -> list[tuple[str, str, str]]:
    """(nombre sin --lb-, valor, comentario) de cada variable --lb-* del bloque indicado."""
    sin_cabecera = re.sub(r"^\s*/\*.*?\*/", "", css, count=1, flags=re.S)
    return [(m.group(1), " ".join(m.group(2).split()), m.group(3) or "")
            for m in DECLARACION.finditer(_bloque(sin_cabecera, selector))]


def _categoria(nombre: str):
    for prefijo, grupo, tipo, por_modo in CATEGORIAS:
        if nombre.startswith(prefijo):
            return prefijo, grupo, tipo, por_modo
    raise ValueError(f"--lb-{nombre}: categoría desconocida (ver CATEGORIAS)")


def _valor(tipo: str, valor: str):
    if tipo != "boxShadow":
        return valor
    capas = [{"x": m.group(1), "y": m.group(2), "blur": m.group(3), "spread": m.group(4) or "0",
              "color": m.group(5).replace(" ", ""), "type": "dropShadow"} for m in SOMBRA.finditer(valor)]
    if not capas:
        raise ValueError(f"sombra no reconocida: {valor}")
    return capas if len(capas) > 1 else capas[0]


def _token(tipo: str, valor: str, comentario: str) -> dict:
    token = {"value": _valor(tipo, valor), "type": tipo}
    if comentario:
        token["description"] = comentario
    return token


def exportar(css: str) -> dict:
    conjuntos: dict[str, dict] = {"global": {}, "claro": {}, "oscuro": {}}
    for nombre, valor, comentario in leer_css(css, ":root"):
        prefijo, grupo, tipo, por_modo = _categoria(nombre)
        destino = conjuntos["claro" if por_modo else "global"]
        destino.setdefault(grupo, {})[nombre[len(prefijo):]] = _token(tipo, valor, comentario)
    for nombre, valor, comentario in leer_css(css, '[data-bs-theme="dark"]'):
        prefijo, grupo, tipo, por_modo = _categoria(nombre)
        if not por_modo:
            raise ValueError(f"--lb-{nombre}: el modo oscuro solo redefine colores y sombras")
        conjuntos["oscuro"].setdefault(grupo, {})[nombre[len(prefijo):]] = _token(tipo, valor, comentario)
    temas = [{"id": "claro", "name": "Claro", "selectedTokenSets": {"global": "enabled", "claro": "enabled"}},
             {"id": "oscuro", "name": "Oscuro", "selectedTokenSets": {"global": "enabled", "oscuro": "enabled"}}]
    return {**conjuntos, "$themes": temas, "$metadata": {"tokenSetOrder": ["global", "claro", "oscuro"]}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comprobar", action="store_true")
    args = parser.parse_args()
    texto = json.dumps(exportar(CSS.read_text(encoding="utf-8")), indent=2, ensure_ascii=False) + "\n"
    if args.comprobar:
        if not JSON.exists() or JSON.read_text(encoding="utf-8") != texto:
            print(f"{JSON} no coincide con {CSS}: ejecuta python scripts/exportar_tokens.py", file=sys.stderr)
            return 1
        return 0
    JSON.write_text(texto, encoding="utf-8", newline="\n")
    datos = json.loads(texto)
    total = sum(len(g) for c in ("global", "claro", "oscuro") for g in datos[c].values())
    print(f"{total} tokens en {JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
