"""Comportamiento del JS del frontend ejecutado en Node con un DOM mínimo simulado.

RF-PUB-12 (contador de caracteres), RF-FED-11 (actualizar a demanda), RF-FED-16 (quitar el filtro),
RF-FED-17 (el filtro se mantiene en las actualizaciones automáticas y manuales) y RF-AUT-45 (Continuar).
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.security.session import get_sesion_opcional

RAIZ = Path(__file__).resolve().parents[2]
requiere_node = pytest.mark.skipif(shutil.which("node") is None, reason="node no disponible")


def _node(script: str, *args: str) -> dict:
    salida = subprocess.run(["node", "-e", script, *args], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(salida.stdout)


CONTADOR_JS = r"""
const vm = require("vm"), fs = require("fs");
const ctx = { console, setInterval: () => 0, Date, URLSearchParams, location: { search: "" },
              document: { addEventListener() {} } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8") + ";globalThis.Banca = Banca;", ctx);
const oyentes = {};
const campo = { value: "  hola  ", addEventListener: (tipo, fn) => { oyentes[tipo] = fn; } };
const salida = { textContent: "" };
ctx.Banca.contador(campo, salida, 80);
const inicial = salida.textContent;
campo.value = "x".repeat(45);
oyentes.input();
console.log(JSON.stringify({ inicial, escrito: salida.textContent }));
"""


@requiere_node
def test_contador_de_caracteres():
    """RF-PUB-12: muestra «usados/máximo» al cargar y mientras se escribe (tras la normalización)."""
    assert _node(CONTADOR_JS, str(RAIZ / "web/static/js/app.js")) == {"inicial": "4/80", "escrito": "45/80"}


FEED_JS = r"""
const vm = require("vm"), fs = require("fs");
const nodo = (id) => {
  const n = { id, value: "", textContent: "", oyentes: {}, oculto: true,
    classList: { toggle(clase, estado) { if (clase === "d-none") n.oculto = estado; } },
    addEventListener(tipo, fn) { (n.oyentes[tipo] = n.oyentes[tipo] || []).push(fn); },
    dispatchEvent(e) { (n.oyentes[e.type] || []).forEach((fn) => fn(e)); },
    click() { n.dispatchEvent({ type: "click" }); },
    replaceChildren() {}, append() {} };
  return n;
};
const nodos = {};
["lista", "vacio", "centinela", "filtro-tipo", "quitar-filtro", "actualizar", "mensajes"].forEach((id) => { nodos[id] = nodo(id); });
const llamadas = [], intervalos = [];
const Banca = {
  TIPOS: { NECESITO: "Necesito", OFREZCO: "Ofrezco", ACTIVIDAD: "Actividad" },
  api: async (url, opciones = {}) => {
    llamadas.push({ url, automatica: !!opciones.automatica });
    return { items: [], siguiente_cursor: null, tamano_bloque: 20, mensaje_vacio: null };
  },
  alerta() {}, limpiar() {}, el: () => ({}), restante: () => "", refrescarRestantes() {},
};
const ctx = { console, Banca, Event: class { constructor(type) { this.type = type; } }, URLSearchParams, Math,
  setInterval: (fn, ms) => intervalos.push({ fn, ms }),
  IntersectionObserver: class { observe() {} },
  document: { visibilityState: "visible", body: { dataset: { pagina: "feed" } }, getElementById: (id) => nodos[id] } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), ctx);
const esperar = () => new Promise((r) => setTimeout(r, 0));
(async () => {
  const pasos = {};
  await esperar();
  pasos.inicial = llamadas.splice(0);
  nodos["filtro-tipo"].value = "OFREZCO";
  nodos["filtro-tipo"].dispatchEvent(new ctx.Event("change"));
  await esperar();
  pasos.filtro = llamadas.splice(0);
  pasos.quitarVisible = !nodos["quitar-filtro"].oculto;
  intervalos.find((i) => i.ms === 60000).fn();  // actualización automática
  await esperar();
  pasos.automatica = llamadas.splice(0);
  nodos["actualizar"].click();  // actualización manual
  await esperar();
  pasos.manual = llamadas.splice(0);
  nodos["quitar-filtro"].click();
  await esperar();
  pasos.quitar = llamadas.splice(0);
  pasos.valorTrasQuitar = nodos["filtro-tipo"].value;
  pasos.quitarOculto = nodos["quitar-filtro"].oculto;
  console.log(JSON.stringify(pasos));
})();
"""


@pytest.fixture(scope="module")
def pasos_feed():
    if shutil.which("node") is None:
        pytest.skip("node no disponible")
    return _node(FEED_JS, str(RAIZ / "web/static/js/feed.js"))


def test_feed_actualizar_a_demanda(pasos_feed):
    """RF-FED-11: el botón Actualizar vuelve a pedir el feed (como interacción, no automática)."""
    assert pasos_feed["inicial"] == [{"url": "/api/feed?", "automatica": False}]
    assert pasos_feed["manual"] == [{"url": "/api/feed?tipo=OFREZCO", "automatica": False}]


def test_feed_filtro_se_mantiene_en_actualizaciones(pasos_feed):
    """RF-FED-17 / RN-45: las actualizaciones automática y manual conservan el filtro aplicado."""
    assert pasos_feed["filtro"] == [{"url": "/api/feed?tipo=OFREZCO", "automatica": False}]
    assert pasos_feed["automatica"] == [{"url": "/api/feed?tipo=OFREZCO", "automatica": True}]
    assert pasos_feed["manual"][0]["url"] == "/api/feed?tipo=OFREZCO"


def test_feed_quitar_filtro(pasos_feed):
    """RF-FED-16: «Ver todos» aparece con un filtro aplicado y restablece Todos."""
    assert pasos_feed["quitarVisible"] is True
    assert pasos_feed["quitar"] == [{"url": "/api/feed?", "automatica": False}]
    assert pasos_feed["valorTrasQuitar"] == "" and pasos_feed["quitarOculto"] is True


def test_activacion_ofrece_continuar_al_inicio_de_sesion():
    """RF-AUT-45: junto a la confirmación de activación hay un control Continuar que lleva a /login."""
    app.dependency_overrides[get_sesion_opcional] = lambda: None
    try:
        html = TestClient(app).get("/activar?token=t").text
    finally:
        app.dependency_overrides.clear()
    bloque = html[html.index('id="continuar"'):]
    bloque = bloque[:bloque.index("</div>")]
    assert 'href="/login"' in bloque and ">Continuar</a>" in bloque
    js = (RAIZ / "web/static/js/acceso.js").read_text(encoding="utf-8")
    exito = js[js.index('api("/api/cuentas/activar"'):js.index(".catch(", js.index('api("/api/cuentas/activar"'))]
    assert 'getElementById("continuar").classList.remove("d-none")' in exito  # se muestra al activar
