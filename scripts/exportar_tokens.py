"""Exporta los tokens de diseño de web/static/css/tokens.css a docs/investigacion/tokens.json.

    python scripts/exportar_tokens.py           # escribe el JSON
    python scripts/exportar_tokens.py --comprobar   # falla si el JSON no coincide con el CSS

Formato de Tokens Studio para Figma: un conjunto «global» con grupos anidados; cada token es
{"value": ..., "type": ..., "description": ...}, más "$themes" y "$metadata.tokenSetOrder". En Tokens Studio:
Settings → Sync → archivo local o repositorio, o «Load from file». Los valores en rem se convierten con la
base de 16 px que Tokens Studio usa por defecto.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "web" / "static" / "css" / "tokens.css"
JSON = RAIZ / "docs" / "investigacion" / "tokens.json"

# prefijo de la variable → (grupo en el JSON, tipo de Tokens Studio)
CATEGORIAS = [
    ("color-", "color", "color"),
    ("fuente-familia-", "fontFamilies", "fontFamilies"),
    ("fuente-tamano-", "fontSizes", "fontSizes"),
    ("fuente-peso-", "fontWeights", "fontWeights"),
    ("interlineado-", "lineHeights", "lineHeights"),
    ("espacio-", "spacing", "spacing"),
    ("radio-", "borderRadius", "borderRadius"),
    ("punto-", "sizing", "sizing"),
]
DECLARACION = re.compile(r"--lb-([a-z0-9-]+):\s*([^;]+);[ \t]*(?:/\*\s*(.*?)\s*\*/)?")


def leer_css(css: str) -> list[tuple[str, str, str]]:
    """(nombre sin --lb-, valor, comentario) de cada variable --lb-* del bloque :root."""
    sin_cabecera = re.sub(r"^\s*/\*.*?\*/", "", css, count=1, flags=re.S)
    return [(m.group(1), " ".join(m.group(2).split()), m.group(3) or "") for m in DECLARACION.finditer(sin_cabecera)]


def exportar(css: str) -> dict:
    grupos: dict[str, dict] = {}
    for nombre, valor, comentario in leer_css(css):
        for prefijo, grupo, tipo in CATEGORIAS:
            if nombre.startswith(prefijo):
                token = {"value": valor, "type": tipo}
                if comentario:
                    token["description"] = comentario
                grupos.setdefault(grupo, {})[nombre[len(prefijo):]] = token
                break
        else:
            raise ValueError(f"--lb-{nombre}: categoría desconocida (ver CATEGORIAS)")
    return {"global": grupos, "$themes": [], "$metadata": {"tokenSetOrder": ["global"]}}


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
    print(f"{sum(len(g) for g in json.loads(texto)['global'].values())} tokens en {JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
