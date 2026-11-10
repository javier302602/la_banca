"""i18n: todos los textos de plantillas y JS salen del catálogo es-PE; fechas y horas con Intl en America/Lima."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.domain.entities import CodigoMotivo, TipoPublicacion
from app.shared.security.session import SesionActual, get_sesion_opcional
from app.shared.web import i18n

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS = sorted((RAIZ / "web" / "templates").rglob("*.html"))
JS = sorted((RAIZ / "web" / "static" / "js").glob("*.js"))
CATALOGO = i18n.catalogo()


# --- catálogo ----------------------------------------------------------------------------------------
def test_solo_es_pe_activo_con_zona_de_lima():
    assert i18n.IDIOMA_ACTIVO == "es-PE" and i18n.IDIOMAS_DISPONIBLES == ("es-PE",)  # SRS: interfaz en español
    assert i18n.ZONA_HORARIA == "America/Lima"
    with pytest.raises(ValueError):
        i18n.catalogo("en-US")


def test_interpolacion_y_clave_inexistente():
    assert i18n.t("app.titulo_pagina", titulo="Ahora") == "Ahora · La Banca"
    assert i18n.t("js.publicaciones.cupo", activas=1, maximo=3) == "Publicaciones activas: {activas} de {maximo}" \
        .replace("{activas}", "1").replace("{maximo}", "3")
    with pytest.raises(KeyError):
        i18n.t("no.existe")


def test_listo_para_otro_idioma(tmp_path, monkeypatch):
    """Agregar un idioma es agregar su archivo con las mismas claves."""
    origen = json.loads((i18n.DIRECTORIO / "es-PE.json").read_text(encoding="utf-8"))
    (tmp_path / "es-PE.json").write_text(json.dumps(origen), encoding="utf-8")
    origen["nav"]["ahora"] = "Now"
    (tmp_path / "en-US.json").write_text(json.dumps(origen), encoding="utf-8")
    monkeypatch.setattr(i18n, "DIRECTORIO", tmp_path)
    monkeypatch.setattr(i18n, "IDIOMAS_DISPONIBLES", ("es-PE", "en-US"))
    i18n.catalogo.cache_clear()
    try:
        assert i18n.t("nav.ahora", idioma="en-US") == "Now" and i18n.t("nav.ahora") == "Ahora"
        assert set(i18n.catalogo("en-US")) == set(i18n.catalogo("es-PE"))
    finally:
        i18n.catalogo.cache_clear()


def test_claves_usadas_en_plantillas_existen():
    usadas = set()
    for plantilla in PLANTILLAS:
        usadas |= set(re.findall(r"""\bt\(\s*["']([\w.]+)["']""", plantilla.read_text(encoding="utf-8")))
    faltan = {c for c in usadas if c not in CATALOGO and not c.endswith((".", "_"))}
    assert not faltan, faltan
    # claves compuestas en las plantillas (`"tipos." ~ valor`, `"motivos." ~ codigo`, …)
    compuestas = [f"tipos.{t.value}" for t in TipoPublicacion] + [f"motivos.{m.value}" for m in CodigoMotivo]
    compuestas += [f"error.{c}.{p}" for c in (404, 405) for p in ("titulo", "mensaje")]
    compuestas += ["reportar.titulo_publicacion", "reportar.titulo_chat"]
    compuestas += [f"ayuda.{p}_{tema}" for p in "pr" for tema in
                   ("activar", "publicacion", "chat", "reporte", "contrasena", "datos")]
    assert all(c in CATALOGO for c in compuestas), [c for c in compuestas if c not in CATALOGO]


def test_claves_usadas_en_js_existen():
    catalogo_js = i18n.catalogo_js()
    usadas = set()
    for archivo in JS:
        usadas |= set(re.findall(r"""\bt\(\s*["'`]([\w.]+)["'`]""", archivo.read_text(encoding="utf-8")))
    usadas |= {f"tipos.{t.value}" for t in TipoPublicacion}  # TIPOS[tipo] → t(`tipos.${tipo}`)
    assert usadas and not (usadas - set(catalogo_js)), usadas - set(catalogo_js)


# --- sin textos fuera del catálogo ---------------------------------------------------------------------
def _texto_visible(html: str) -> str:
    html = re.sub(r"\{% block pagina %\}.*?\{% endblock %\}", " ", html)  # identificador técnico (data-pagina)
    sin_jinja = re.sub(r"\{#.*?#\}|\{%.*?%\}|\{\{.*?\}\}", " ", html, flags=re.S)
    sin_script = re.sub(r"<script.*?</script>", " ", sin_jinja, flags=re.S)
    return re.sub(r"<[^>]+>", " ", sin_script)


@pytest.mark.parametrize("plantilla", PLANTILLAS, ids=lambda p: p.relative_to(RAIZ / "web" / "templates").as_posix())
def test_plantillas_sin_textos_literales(plantilla):
    html = plantilla.read_text(encoding="utf-8")
    sobrante = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ¿¡]{2,}", _texto_visible(html))
    assert not sobrante, sobrante
    atributos = re.findall(r'\b(?:placeholder|aria-label|title|alt)="([^"{]*[A-Za-zÁ-ú][^"]*)"', html)
    assert not atributos, atributos


TECNICOS = {"Accept", "POST", "GET", "PATCH", "Content-Type"}


def _literales(js: str) -> list[str]:
    sin_comentarios = re.sub(r"/\*.*?\*/|(?<![:\"'])//[^\n]*", " ", js, flags=re.S)
    return re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`([^`]*)`', sin_comentarios)


@pytest.mark.parametrize("archivo", JS, ids=lambda p: p.name)
def test_js_sin_textos_literales(archivo):
    """Un literal con tildes, ñ, ¿/¡ o palabras en mayúscula inicial es texto para la persona usuaria."""
    sospechosos = []
    for grupos in _literales(archivo.read_text(encoding="utf-8")):
        texto = re.sub(r"\$\{[^}]*\}", "", next(g for g in grupos if g is not None) if any(grupos) else "")
        if not texto or texto in TECNICOS or texto.startswith(("/", "#", ".", "[", "image/", "data:")):
            continue
        if re.search(r"[áéíóúñÁÉÍÓÚÑ¿¡]", texto) or re.search(r"(^|\s)[A-ZÁÉÍÓÚ][a-záéíóúñ]+(\s|$)", texto):
            sospechosos.append(texto)
    assert not sospechosos, sospechosos


# --- páginas ---------------------------------------------------------------------------------------------
@pytest.fixture
def cliente():
    app.dependency_overrides[get_sesion_opcional] = lambda: SesionActual("s1", "u1", "ana_07")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("ruta", ["/feed", "/chats", "/publicaciones/nueva", "/ayuda", "/terminos"])
def test_paginas_en_es_pe_con_catalogo(cliente, ruta):
    html = cliente.get(ruta).text
    assert '<html lang="es-PE"' in html and 'data-zona-horaria="America/Lima"' in html
    incrustado = json.loads(re.search(r'<script id="i18n" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert incrustado == i18n.catalogo_js()


# --- Intl en America/Lima ---------------------------------------------------------------------------------
INTL_JS = r"""
const vm = require("vm"), fs = require("fs");
const ctx = { console, setInterval: () => 0, Date, Intl, URLSearchParams, location: { search: "" },
  document: { addEventListener() {}, getElementById: (id) => (id === "i18n" ? { textContent: process.env.CATALOGO_I18N } : null) } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8") + ";globalThis.Banca = Banca;", ctx);
const B = ctx.Banca;
console.log(JSON.stringify({
  hora: B.formatoHora("2026-10-03T03:30:00Z"), mediodia: B.formatoHora("2026-10-02T17:05:00Z"),
  fecha: B.formatoFecha("2026-11-01"), fechaHora: B.formatoFecha("2026-11-02T03:00:00Z"),
  tipo: B.TIPOS.NECESITO, sistema: Intl.DateTimeFormat().resolvedOptions().timeZone,
}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node no disponible")
@pytest.mark.parametrize("zona_del_sistema", ["Asia/Tokyo", "UTC", "America/Lima"])
def test_intl_formatea_en_lima_sin_importar_la_zona_del_dispositivo(zona_del_sistema):
    entorno = {**os.environ, "TZ": zona_del_sistema, "CATALOGO_I18N": json.dumps(i18n.catalogo_js())}
    salida = subprocess.run(["node", "-e", INTL_JS, str(RAIZ / "web/static/js/app.js")], capture_output=True,
                            text=True, check=True, timeout=30, env=entorno)
    datos = json.loads(salida.stdout)
    assert datos["sistema"] == zona_del_sistema  # el «dispositivo» está en otra zona…
    assert (datos["hora"], datos["mediodia"]) == ("22:30", "12:05")  # …y la hora se muestra en Lima (RN-34)
    assert datos["fecha"] == "1 de noviembre de 2026"
    assert datos["fechaHora"] == "1 de noviembre de 2026"  # 03:00 UTC del 2 = 22:00 del 1 en Lima
    assert datos["tipo"] == "Necesito"
