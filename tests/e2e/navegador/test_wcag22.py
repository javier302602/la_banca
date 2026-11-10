"""WCAG 2.2 AA en el navegador: axe-core con los tags hasta wcag22aa y pruebas propias de los criterios nuevos
(2.4.11, 2.5.8, 3.2.6, 3.3.7 y 3.3.8). Ver docs/investigacion/02_wcag_i18n.md."""
import pytest

from tests.e2e.navegador.conftest import CLAVE, iniciar_sesion, publicar, responder
from tests.e2e.navegador.test_accesibilidad import paginas

TAGS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


@pytest.fixture(scope="module")
def escenario(navegador, servidor, usuarios):
    autor, lector = navegador.new_context(base_url=servidor), navegador.new_context(base_url=servidor)
    try:
        iniciar_sesion(autor, "beto@unas.edu.pe")
        iniciar_sesion(lector, "ana@unas.edu.pe")
        pid = publicar(autor, "Busco grupo de estudio de física", "NECESITO")
        chat = responder(lector, pid, "Me apunto")
        publicar(lector, "Ofrezco clases de cálculo", "OFREZCO")
        return {"pid": pid, "chat": chat}
    finally:
        autor.close()
        lector.close()


def todas(e):
    return paginas(e) + [("/ayuda", None, "article"), ("/ayuda", "ana@unas.edu.pe", "article")]


def _abrir(navegador, servidor, ruta, correo, listo, **opciones):
    contexto = navegador.new_context(base_url=servidor, locale="es-PE", **opciones)
    if correo:
        iniciar_sesion(contexto, correo)
    pagina = contexto.new_page()
    pagina.goto(ruta)
    pagina.locator(listo).first.wait_for()
    return contexto, pagina


def test_axe_wcag22aa_sin_violaciones(navegador, servidor, escenario):
    """Todas las reglas de axe-core etiquetadas WCAG 2.0, 2.1 y 2.2 niveles A y AA (incluye target-size)."""
    from axe_playwright_python.sync_playwright import Axe

    axe, hallazgos = Axe(), []
    for ruta, correo, listo in todas(escenario):
        for ancho in (360, 1366):
            contexto, pagina = _abrir(navegador, servidor, ruta, correo, listo, viewport={"width": ancho, "height": 900})
            try:
                resultado = axe.run(pagina, options={"runOnly": {"type": "tag", "values": TAGS_WCAG}})
                for v in resultado.response["violations"]:
                    hallazgos.append((ruta, ancho, v["id"], v["impact"], [n["target"] for n in v["nodes"]][:3]))
            finally:
                contexto.close()
    assert not hallazgos, hallazgos


TAMANOS_JS = """() => {
  const visibles = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea')]
    .filter((n) => n.getClientRects().length && getComputedStyle(n).visibility !== 'hidden');
  const enLinea = (n) => n.tagName === 'A' && [...n.parentElement.childNodes]
    .some((h) => h !== n && h.nodeType === 3 && h.textContent.trim());  // enlace dentro de una frase
  return visibles.filter((n) => !enLinea(n)).map((n) => {
    const r = n.getBoundingClientRect();
    return { id: n.id || n.name || n.textContent.trim().slice(0, 30), ancho: r.width, alto: r.height };
  }).filter((r) => r.ancho < 24 || r.alto < 24);
}"""


def test_2_5_8_objetivos_de_al_menos_24_px(navegador, servidor, escenario):
    pequenos = []
    for ruta, correo, listo in todas(escenario):
        for ancho in (360, 1366):
            contexto, pagina = _abrir(navegador, servidor, ruta, correo, listo, viewport={"width": ancho, "height": 900})
            try:
                if ancho == 360 and correo:
                    pagina.click(".navbar-toggler")  # también los enlaces del menú desplegado
                    pagina.locator("#nav-principal.show").wait_for()
                pequenos += [(ruta, ancho, p) for p in pagina.evaluate(TAMANOS_JS)]
            finally:
                contexto.close()
    assert not pequenos, pequenos


FOCO_VISIBLE_JS = """() => {
  const n = document.activeElement;
  if (!n || n === document.body) return null;
  const r = n.getBoundingClientRect();
  const x = Math.min(Math.max(r.left + r.width / 2, 0), innerWidth - 1);
  const y = Math.min(Math.max(r.top + r.height / 2, 0), innerHeight - 1);
  const encima = document.elementFromPoint(x, y);
  const dentro = r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
  return { id: n.id || n.textContent.trim().slice(0, 30), visible: dentro && !!encima && (encima === n || n.contains(encima) || encima.contains(n)) };
}"""


def test_2_4_11_el_foco_no_queda_oculto(navegador, servidor, escenario):
    """Recorriendo cada página con Tab, el elemento con foco está en pantalla y nada lo tapa."""
    ocultos = []
    for ruta, correo, listo in todas(escenario):
        # Con movimiento reducido: sin el desplazamiento suave de Bootstrap, el foco ya está en su sitio al medir
        contexto, pagina = _abrir(navegador, servidor, ruta, correo, listo, viewport={"width": 360, "height": 640},
                                  reduced_motion="reduce")
        try:
            vistos = set()
            for _ in range(40):
                pagina.keyboard.press("Tab")
                estado = pagina.evaluate(FOCO_VISIBLE_JS)
                if estado is None or estado["id"] in vistos:
                    continue
                vistos.add(estado["id"])
                if not estado["visible"]:
                    ocultos.append((ruta, estado["id"]))
        finally:
            contexto.close()
    assert not ocultos, ocultos


def test_3_2_6_ayuda_en_el_mismo_lugar(navegador, servidor, escenario):
    for ruta, correo, listo in todas(escenario):
        contexto, pagina = _abrir(navegador, servidor, ruta, correo, listo)
        try:
            enlaces = pagina.locator("footer nav.pie-enlaces a")
            assert [enlaces.nth(i).get_attribute("href") for i in range(enlaces.count())] == ["/terminos", "/ayuda"], ruta
            assert enlaces.nth(1).inner_text() == "Ayuda"
        finally:
            contexto.close()
    contexto, pagina = _abrir(navegador, servidor, "/ayuda", None, "article")
    try:
        assert pagina.locator("article section h2").count() == 6
    finally:
        contexto.close()


def test_3_3_7_el_correo_no_se_vuelve_a_escribir(contexto, pagina, usuarios):
    """El correo escrito al iniciar sesión se propone al recuperar la contraseña y al pedir un enlace de
    activación (misma pestaña)."""
    pagina.goto("/login")
    pagina.fill("#correo", "ana@unas.edu.pe")
    pagina.locator("#correo").dispatch_event("change")
    pagina.click("a[href='/recuperar']")
    pagina.wait_for_url("**/recuperar")
    assert pagina.input_value("#correo") == "ana@unas.edu.pe"
    pagina.goto("/activar")
    assert pagina.input_value("#correo") == "ana@unas.edu.pe"


@pytest.mark.parametrize("ruta,campos", [
    ("/login", {"correo": "username", "contrasena": "current-password"}),
    ("/registro", {"correo": "email", "contrasena": "new-password", "confirmacion": "new-password"}),
    ("/restablecer?token=t", {"contrasena": "new-password", "confirmacion": "new-password"}),
    ("/recuperar", {"correo": "email"}),
])
def test_3_3_8_autenticacion_accesible(pagina, ruta, campos):
    """Se puede pegar y usar el gestor de contraseñas: autocomplete correcto y el pegado no se bloquea."""
    pagina.goto(ruta)
    for campo, autocompletar in campos.items():
        control = pagina.locator(f"#{campo}")
        assert control.get_attribute("autocomplete") == autocompletar
        assert control.get_attribute("onpaste") is None
        bloqueado = control.evaluate("""n => { const e = new Event('paste', { bubbles: true, cancelable: true });
                                               n.dispatchEvent(e); return e.defaultPrevented; }""")
        assert bloqueado is False
        control.focus()
        pagina.keyboard.insert_text(CLAVE)  # lo que inserta el pegado o un gestor de contraseñas
        assert control.input_value() == CLAVE


def test_i18n_selector_de_imagen_y_hora_en_lima(navegador, servidor, escenario, tmp_path):
    """Los textos del selector de imagen salen del catálogo (no del idioma del navegador) y la hora de los
    mensajes se muestra en America/Lima aunque el navegador esté en otra zona."""
    contexto = navegador.new_context(base_url=servidor, locale="en-US", timezone_id="Asia/Tokyo")
    try:
        iniciar_sesion(contexto, "ana@unas.edu.pe")
        p = contexto.new_page()
        p.goto(f"/chats/{escenario['chat']}")
        p.locator("#historial .burbuja").first.wait_for()
        assert p.inner_text(".boton-archivo") == "Elegir imagen"
        assert p.inner_text("#nombre-archivo") == "Ningún archivo seleccionado"
        imagen = tmp_path / "foto.png"
        imagen.write_bytes(bytes.fromhex("89504e470d0a1a0a"))
        p.set_input_files("#imagen", str(imagen))
        assert p.inner_text("#nombre-archivo") == "foto.png"
        esperado = contexto.request.get(f"/api/chats/{escenario['chat']}").json()["mensajes"][0]["hora"]  # Lima
        assert p.inner_text("#historial .burbuja .hora") == esperado
        assert p.evaluate("document.documentElement.lang") == "es-PE"
    finally:
        contexto.close()
