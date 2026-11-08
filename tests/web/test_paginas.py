"""Fase 8 — Frontend: vistas Jinja2 que extienden base.html y JS con Fetch API."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app
from app.shared.security.session import SesionActual, get_sesion_opcional

RAIZ = Path(__file__).resolve().parents[2]
SESION = SesionActual("s1", "u1", "ana_07")

PRIVADAS = {
    "/feed": ("feed.js", "Ahora"),
    "/publicaciones/nueva": ("publicaciones.js", "Tu publicación estará activa durante 24 horas"),
    "/publicaciones/mias": ("publicaciones.js", "Mis publicaciones activas"),
    "/publicaciones/abc123": ("feed.js", "Volver al feed"),
    "/publicaciones/abc123/responder": ("chat.js", "Primer mensaje"),
    "/publicaciones/abc123/reportar": ("reportes.js", "Reportar publicación"),
    "/chats": ("chat.js", "Mis chats"),
    "/chats/c1": ("chat.js", "Escribe un mensaje"),
    "/chats/c1/reportar": ("reportes.js", "Reportar chat"),
    "/perfil": ("acceso.js", "Mi perfil"),
}
PUBLICAS = {
    "/login": "Iniciar sesión", "/registro": "Crear cuenta", "/activar": "Solicitar un nuevo enlace de activación",
    "/recuperar": "Recuperar contraseña", "/restablecer?token=t": "Nueva contraseña",
    "/terminos": "Términos de uso y política de privacidad",
}


@pytest.fixture
def cliente():
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


def con_sesion(sesion=SESION):
    app.dependency_overrides[get_sesion_opcional] = lambda: sesion


def sin_sesion(motivo=None):
    def dependencia(request: Request):
        if motivo:
            request.state.motivo_sin_sesion = motivo
        return None

    app.dependency_overrides[get_sesion_opcional] = dependencia


@pytest.mark.parametrize("ruta", PRIVADAS)
def test_paginas_privadas_extienden_base_y_cargan_su_js(cliente, ruta):
    con_sesion()
    respuesta = cliente.get(ruta)
    script, texto = PRIVADAS[ruta]
    assert respuesta.status_code == 200, respuesta.text
    html = respuesta.text
    assert "bootstrap@5.3.3" in html and "/static/js/app.js" in html and f"/static/js/{script}" in html
    assert texto in html and "@ana_07" in html and "data-cerrar-sesion" in html


@pytest.mark.parametrize("ruta", PRIVADAS)
def test_paginas_privadas_sin_sesion_redirigen(cliente, ruta):
    sin_sesion()
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/login"


def test_redireccion_por_inactividad_muestra_aviso(cliente):
    sin_sesion("sesion_expirada")
    assert cliente.get("/feed").headers["location"] == "/login?motivo=inactividad"
    assert "Tu sesión se cerró por inactividad" in cliente.get("/login?motivo=inactividad").text  # RF-AUT-23


@pytest.mark.parametrize("ruta", PUBLICAS)
def test_paginas_publicas(cliente, ruta):
    sin_sesion()
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200 and PUBLICAS[ruta] in respuesta.text


def test_login_y_registro_con_sesion_van_al_feed(cliente):
    con_sesion()
    for ruta in ("/login", "/registro"):
        assert cliente.get(ruta).headers["location"] == "/feed"
    assert cliente.get("/").headers["location"] == "/feed"
    sin_sesion()
    assert cliente.get("/").headers["location"] == "/login"


def test_nickname_se_escapa(cliente):
    con_sesion(SesionActual("s1", "u1", "<script>alert(1)</script>"))
    html = cliente.get("/feed").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html  # RNF-SEG-05


def test_registro_casilla_desmarcada(cliente):
    sin_sesion()
    html = cliente.get("/registro").text
    casilla = html[html.index('id="acepta_terminos"') - 80: html.index('id="acepta_terminos"') + 40]
    assert "checked" not in casilla  # RF-AUT-16


def test_crear_publicacion_sin_duracion_ni_tipo_preseleccionado(cliente):
    con_sesion()
    html = cliente.get("/publicaciones/nueva").text
    assert "duracion" not in html.lower() and "checked" not in html  # RF-PUB-02 / RF-PUB-14
    for tipo in ("NECESITO", "OFREZCO", "ACTIVIDAD"):
        assert f'value="{tipo}"' in html


def test_feed_ofrece_todos_y_los_tres_tipos(cliente):
    con_sesion()
    html = cliente.get("/feed").text
    assert '<option value="" selected>Todos</option>' in html  # RF-FED-18
    assert all(f'value="{t}"' in html for t in ("NECESITO", "OFREZCO", "ACTIVIDAD"))


def test_reportar_ofrece_los_cinco_motivos(cliente):
    con_sesion()
    html = cliente.get("/chats/c1/reportar").text
    for nombre in ("Contenido inapropiado", "Acoso o comportamiento ofensivo", "Spam", "Fraude o engaño", "Otro"):
        assert nombre in html
    assert 'data-url="/api/chats/c1/reportes"' in html


def test_terminos_muestran_version_y_texto(cliente):
    sin_sesion()
    html = cliente.get("/terminos").text
    assert "Versión" in html and "Correo institucional" in html


def test_archivos_estaticos(cliente):
    js = {n: cliente.get(f"/static/js/{n}").text for n in ("app.js", "feed.js", "chat.js")}
    assert "X-Actualizacion-Automatica" in js["app.js"] and "textContent" in js["app.js"]
    assert "60000" in js["feed.js"] and "IntersectionObserver" in js["feed.js"]  # RF-FED-08 / RF-FED-19
    assert "setTimeout(sondear, 1000)" in js["chat.js"] and "visibilityState" in js["chat.js"]
    assert "innerHTML" not in "".join(js.values())  # RNF-SEG-05
    assert cliente.get("/static/css/app.css").status_code == 200


@pytest.mark.skipif(shutil.which("node") is None, reason="node no disponible")
def test_utilidades_js_con_node():
    script = """
    const vm = require("vm");
    const fs = require("fs");
    const ctx = { console, setInterval: () => 0, Date, URLSearchParams, location: { search: "" },
                  document: { addEventListener() {} }, fetch: async () => ({}) };
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(process.argv[1], "utf8") + ";globalThis.Banca = Banca;", ctx);
    const B = ctx.Banca;
    B.sincronizar(new Date(Date.now()).toISOString());
    const en = (min) => new Date(Date.now() + min * 60000).toISOString();
    console.log(JSON.stringify({
      r1: B.restante(en(9.2)), r2: B.restante(en(124.5)), r3: B.restante(en(-1)),
      horaLocal: typeof B.horaHHMM,
    }));
    """
    salida = subprocess.run(["node", "-e", script, str(RAIZ / "web/static/js/app.js")],
                            capture_output=True, text=True, check=True, timeout=30)
    datos = json.loads(salida.stdout)
    assert datos == {"r1": "10 min", "r2": "2 h 5 min", "r3": "Expirada",
                     "horaLocal": "undefined"}  # RN-34: la hora HH:MM ya no se calcula en el navegador


COMPRESION_JS = r"""
const vm = require("vm");
const fs = require("fs");
const soportaWebp = process.argv[2] === "webp";
// Tamaño simulado del resultado: proporcional a los píxeles y a la calidad
const lienzo = () => ({ width: 0, height: 0,
  toDataURL(tipo) { return soportaWebp && tipo === "image/webp" ? "data:image/webp;base64,AA" : "data:image/png;base64,AA"; },
  getContext() { return { drawImage() {} }; },
  toBlob(cb, tipo, calidad) { cb(new Blob([new Uint8Array(Math.round(this.width * this.height * calidad))], { type: tipo })); } });
const ctx = { console, setInterval: () => 0, Date, URLSearchParams, Blob, File, Math, Promise,
  location: { search: "" }, document: { addEventListener() {}, createElement: lienzo },
  createImageBitmap: async () => ({ width: 6000, height: 4000, close() { ctx.cerrado = true; } }) };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8") + ";globalThis.Banca = Banca;", ctx);
(async () => {
  const pequeno = new File([new Uint8Array(1000)], "a.png", { type: "image/png" });
  const grande = new File([new Uint8Array(4 * 1024 * 1024 + 1)], "foto.HEIC.jpg", { type: "image/jpeg" });
  const igual = await ctx.Banca.comprimirImagen(pequeno);
  const r = await ctx.Banca.comprimirImagen(grande);
  console.log(JSON.stringify({ mismo: igual === pequeno, tipo: r.type, nombre: r.name, bytes: r.size,
                               limite: ctx.Banca.LIMITE_SUBIDA, cerrado: !!ctx.cerrado }));
})();
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node no disponible")
@pytest.mark.parametrize("soporte,tipo,extension", [("webp", "image/webp", ".webp"), ("sin-webp", "image/jpeg", ".jpg")])
def test_comprime_imagenes_de_mas_de_4mb(soporte, tipo, extension):
    salida = subprocess.run(["node", "-e", COMPRESION_JS, str(RAIZ / "web/static/js/app.js"), soporte],
                            capture_output=True, text=True, check=True, timeout=30)
    r = json.loads(salida.stdout)
    assert r["mismo"]  # ≤ 4 MB: se sube tal cual
    assert r["tipo"] == tipo and r["nombre"] == f"foto.HEIC{extension}" and r["cerrado"]
    assert 0 < r["bytes"] <= r["limite"] == 4 * 1024 * 1024


def test_chat_comprime_antes_de_subir(cliente):
    js = cliente.get("/static/js/chat.js").text
    assert "await Banca.comprimirImagen(original)" in js and js.count("await datosMensaje()") == 2
