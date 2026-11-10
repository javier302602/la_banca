"""Tokens de diseño: tokens.css es la fuente; tokens.json (Tokens Studio para Figma) está sincronizado y app.css
solo usa tokens. Media queries mobile-first en 768 y 1024 px."""
import importlib.util
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

RAIZ = Path(__file__).resolve().parents[2]
TOKENS_CSS = (RAIZ / "web/static/css/tokens.css").read_text(encoding="utf-8")
APP_CSS = (RAIZ / "web/static/css/app.css").read_text(encoding="utf-8")
TOKENS_JSON = json.loads((RAIZ / "docs/investigacion/tokens.json").read_text(encoding="utf-8"))
TIPOS_TOKENS_STUDIO = {"color", "fontFamilies", "fontSizes", "fontWeights", "lineHeights", "spacing", "borderRadius",
                       "sizing"}

_spec = importlib.util.spec_from_file_location("exportar_tokens", RAIZ / "scripts" / "exportar_tokens.py")
exportar_tokens = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exportar_tokens)


def _sin_comentarios(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def test_tokens_json_sincronizado_con_tokens_css():
    assert exportar_tokens.exportar(TOKENS_CSS) == TOKENS_JSON, "ejecuta python scripts/exportar_tokens.py"


def test_formato_tokens_studio():
    assert TOKENS_JSON["$metadata"] == {"tokenSetOrder": ["global"]} and TOKENS_JSON["$themes"] == []
    hojas = [(grupo, nombre, token) for grupo, tokens in TOKENS_JSON["global"].items() for nombre, token in tokens.items()]
    assert len(hojas) >= 40
    for grupo, nombre, token in hojas:
        assert set(token) <= {"value", "type", "description"} and token["type"] in TIPOS_TOKENS_STUDIO, (grupo, nombre)
        assert token["type"] == grupo, (grupo, nombre)
        if token["type"] == "color":
            assert re.fullmatch(r"#[0-9a-f]{6}", token["value"]), (nombre, token["value"])
        if token["type"] in ("fontSizes", "spacing", "borderRadius", "sizing"):
            assert re.fullmatch(r"\d+(\.\d+)?(rem|px)", token["value"]), (nombre, token["value"])
    assert TOKENS_JSON["global"]["sizing"]["tableta"]["value"] == "768px"
    assert TOKENS_JSON["global"]["sizing"]["escritorio"]["value"] == "1024px"


def test_app_css_sin_colores_literales_y_solo_tokens_existentes():
    css = _sin_comentarios(APP_CSS)
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
    usados = set(re.findall(r"var\(--lb-([a-z0-9-]+)", css))
    definidos = {nombre for nombre, _, _ in exportar_tokens.leer_css(TOKENS_CSS)}
    assert usados and not (usados - definidos), usados - definidos
    assert {"color-primario", "espacio-4", "fuente-tamano-xl", "radio-lg"} <= usados


def test_mobile_first_con_los_puntos_de_quiebre_del_diseno():
    css = _sin_comentarios(APP_CSS)
    consultas = re.findall(r"@media\s*\(([^)]*)\)", css)
    anchos = [c for c in consultas if "width" in c]
    assert anchos and all(c.replace(" ", "") in ("min-width:768px", "min-width:1024px") for c in anchos), anchos
    assert "max-width:" not in "".join(c.replace(" ", "") for c in anchos)  # nada «desktop-first»


def test_base_carga_tokens_antes_que_app_css():
    from app.shared.security.session import get_sesion_opcional

    app.dependency_overrides[get_sesion_opcional] = lambda: None
    try:
        html = TestClient(app).get("/terminos").text
    finally:
        app.dependency_overrides.clear()
    assert html.index("/static/css/tokens.css") < html.index("/static/css/app.css")
    assert TestClient(app).get("/static/css/tokens.css").status_code == 200


def test_plantillas_sin_rejilla_de_bootstrap_ni_anchos_en_linea():
    """Los anchos se rigen por los contenedores propios (360/768/1024), no por los breakpoints de Bootstrap."""
    for plantilla in (RAIZ / "web/templates").rglob("*.html"):
        html = plantilla.read_text(encoding="utf-8")
        assert not re.search(r"\bcol-(sm|md|lg|xl)-\d+|style=\"max-width", html), plantilla.name
    assert "col-md" not in (RAIZ / "web/static/js/feed.js").read_text(encoding="utf-8")
