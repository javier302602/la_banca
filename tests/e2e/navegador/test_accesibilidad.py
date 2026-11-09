"""RNF-USA-02 (360 px sin desplazamiento horizontal), RNF-USA-04 (contraste, axe-core), RNF-USA-07 (etiquetas,
axe-core) y RNF-USA-08 (flujo principal solo con teclado)."""
import re

import pytest

from tests.e2e.navegador.conftest import iniciar_sesion, publicar, responder

# Reglas de axe-core sobre contraste y etiquetas de controles
REGLAS_CONTRASTE_Y_ETIQUETAS = {"color-contrast", "label", "select-name", "aria-input-field-name",
                                "form-field-multiple-labels", "label-title-only", "button-name", "link-name",
                                "input-button-name", "aria-toggle-field-name"}


@pytest.fixture(scope="module")
def escenario(navegador, servidor, usuarios):
    """Una publicación de beto con un chat de ana, para poder abrir todas las pantallas."""
    autor, lector = navegador.new_context(base_url=servidor), navegador.new_context(base_url=servidor)
    try:
        iniciar_sesion(autor, "beto@unas.edu.pe")
        iniciar_sesion(lector, "ana@unas.edu.pe")
        pid = publicar(autor, "Busco grupo de estudio de física para el examen del viernes", "NECESITO")
        chat = responder(lector, pid, "Me apunto, ¿dónde se juntan?")
        publicar(lector, "Ofrezco clases de cálculo", "OFREZCO")
        return {"pid": pid, "chat": chat}
    finally:
        autor.close()
        lector.close()


def paginas(e):
    """(ruta, correo con sesión o None, selector que indica que la página terminó de cargar)."""
    return [
        ("/login", None, "#form-login"), ("/registro", None, "#form-registro"),
        ("/recuperar", None, "#form-recuperar"), ("/activar", None, "#form-reenvio"),
        ("/restablecer?token=t", None, "#form-restablecer"), ("/terminos", None, "article"),
        ("/no-existe", None, "text=Página no encontrada"),
        ("/feed", "ana@unas.edu.pe", ".tarjeta-publicacion"),
        (f"/publicaciones/{e['pid']}", "ana@unas.edu.pe", "#detalle:not(.d-none)"),
        ("/publicaciones/nueva", "ana@unas.edu.pe", "#cupo:has-text('Publicaciones activas')"),
        ("/publicaciones/mias", "ana@unas.edu.pe", "#lista li"),
        ("/chats", "ana@unas.edu.pe", "#lista a"),
        (f"/chats/{e['chat']}", "ana@unas.edu.pe", "#historial .burbuja"),
        (f"/publicaciones/{e['pid']}/responder", "caro@unas.edu.pe", "#form-mensaje"),
        (f"/publicaciones/{e['pid']}/reportar", "ana@unas.edu.pe", "#form-reporte"),
        (f"/chats/{e['chat']}/reportar", "ana@unas.edu.pe", "#form-reporte"),
        ("/perfil", "ana@unas.edu.pe", "#form-nickname"),
    ]


def _abrir(navegador, servidor, ruta, correo, listo, **opciones):
    contexto = navegador.new_context(base_url=servidor, locale="es-PE", **opciones)
    if correo:
        iniciar_sesion(contexto, correo)
    pagina = contexto.new_page()
    pagina.goto(ruta)
    pagina.locator(listo).first.wait_for()
    return contexto, pagina


def test_360_px_sin_desplazamiento_horizontal(navegador, servidor, escenario):
    """RNF-USA-02: en 360 px ninguna pantalla se desborda en horizontal y el menú sigue disponible."""
    desbordes = []
    for ruta, correo, listo in paginas(escenario):
        contexto, pagina = _abrir(navegador, servidor, ruta, correo, listo, viewport={"width": 360, "height": 740})
        try:
            anchos = pagina.evaluate("""() => ({doc: document.documentElement.scrollWidth,
                                               cuerpo: document.body.scrollWidth, vista: window.innerWidth})""")
            if max(anchos["doc"], anchos["cuerpo"]) > anchos["vista"]:
                desbordes.append((ruta, anchos))
            if correo:  # el menú colapsado se puede abrir y ofrece todas las secciones
                pagina.click(".navbar-toggler")
                for enlace in ("Ahora", "Publicar", "Mis publicaciones", "Mis chats", "Cerrar sesión"):
                    pagina.get_by_role("link", name=enlace).or_(pagina.get_by_role("button", name=enlace)) \
                        .first.wait_for(state="visible")
        finally:
            contexto.close()
    assert not desbordes, desbordes


def test_axe_sin_violaciones_serias_de_contraste_ni_etiquetas(navegador, servidor, escenario):
    """RNF-USA-04 / RNF-USA-07: axe-core no encuentra violaciones serias o críticas de contraste ni de etiquetas."""
    from axe_playwright_python.sync_playwright import Axe

    axe, hallazgos = Axe(), []
    for ruta, correo, listo in paginas(escenario):
        for ancho in (360, 1366):
            contexto, pagina = _abrir(navegador, servidor, ruta, correo, listo,
                                      viewport={"width": ancho, "height": 900})
            try:
                for v in axe.run(pagina).response["violations"]:
                    if v["id"] in REGLAS_CONTRASTE_Y_ETIQUETAS and v["impact"] in ("serious", "critical"):
                        hallazgos.append((ruta, ancho, v["id"], [(n["target"], n.get("any", [{}])[0].get("message", "")[:160]) for n in v["nodes"]][:3]))
            finally:
                contexto.close()
    assert not hallazgos, hallazgos


def _tab_hasta(pagina, selector: str, maximo: int = 40) -> None:
    """Mueve el foco con el teclado hasta el elemento indicado (falla si no es alcanzable).

    Avanza con Tab o, si el elemento está antes que el foco actual, retrocede con Shift+Tab, como haría una
    persona (Firefox no vuelve al principio de la página tras el último control: pasa a la barra del navegador).
    Si no lo alcanza en ese sentido, prueba el contrario.
    """
    objetivo = pagina.locator(selector).first
    objetivo.wait_for()
    antes = objetivo.evaluate("n => !!(document.activeElement && document.activeElement !== document.body"
                              " && (n.compareDocumentPosition(document.activeElement) & Node.DOCUMENT_POSITION_FOLLOWING))")
    for tecla in (("Shift+Tab", "Tab") if antes else ("Tab", "Shift+Tab")):
        for _ in range(maximo):
            pagina.keyboard.press(tecla)
            if objetivo.evaluate("n => n === document.activeElement"):
                return
    raise AssertionError(f"{selector} no es alcanzable con el teclado")


def test_flujo_principal_solo_con_teclado(navegador, servidor, usuarios):
    """RNF-USA-08: iniciar sesión, publicar, responder, chatear y reportar usando solo el teclado (PC)."""
    if navegador.browser_type.name == "webkit":
        pytest.skip("RNF-USA-08 aplica a navegadores de PC (Chrome, Firefox y Edge según RNF-COM-01); en WebKit, "
                    "como en Safari por defecto, Tab no recorre los enlaces y Playwright no emula Opción+Tab")
    def contexto():
        return navegador.new_context(base_url=servidor, viewport={"width": 1366, "height": 900})

    autor, lector = contexto(), contexto()
    try:
        # Autor: inicia sesión y publica
        p = autor.new_page()
        p.goto("/login")
        _tab_hasta(p, "#correo")
        p.keyboard.type("beto@unas.edu.pe")
        p.keyboard.press("Tab")
        p.keyboard.type("clave123")
        p.keyboard.press("Enter")
        p.wait_for_url("**/feed")
        _tab_hasta(p, "a.nav-link[href='/publicaciones/nueva']")
        p.keyboard.press("Enter")
        p.wait_for_url("**/publicaciones/nueva")
        _tab_hasta(p, "#tipo-NECESITO")
        p.keyboard.press("Space")
        _tab_hasta(p, "#titulo")
        p.keyboard.type("Necesito un cargador USB-C")
        p.keyboard.press("Tab")
        p.keyboard.type("Solo por una hora, en la biblioteca")
        _tab_hasta(p, "#form-publicacion button[type=submit]")
        p.keyboard.press("Enter")
        p.wait_for_url(re.compile(r"/publicaciones/[0-9a-f]{24}$"))
        publicacion = p.url.rsplit("/", 1)[1]

        # Lector: inicia sesión, abre la publicación desde el feed, responde, chatea y reporta
        q = lector.new_page()
        q.goto("/login")
        _tab_hasta(q, "#correo")
        q.keyboard.type("caro@unas.edu.pe")
        q.keyboard.press("Tab")
        q.keyboard.type("clave123")
        q.keyboard.press("Enter")
        q.wait_for_url("**/feed")
        q.locator(f"a[href='/publicaciones/{publicacion}']").wait_for()
        _tab_hasta(q, f"a[href='/publicaciones/{publicacion}']", maximo=80)
        q.keyboard.press("Enter")
        q.wait_for_url(f"**/publicaciones/{publicacion}")
        _tab_hasta(q, "#acciones a:has-text('Responder')")
        q.keyboard.press("Enter")
        q.wait_for_url("**/responder")
        _tab_hasta(q, "#texto")
        q.keyboard.type("Te lo presto, estoy en la sala 2")
        _tab_hasta(q, "#form-mensaje button[type=submit]")
        q.keyboard.press("Enter")
        q.wait_for_url("**/chats/*")
        q.locator("#historial .burbuja").first.wait_for()
        _tab_hasta(q, "#texto")
        q.keyboard.type("¿Te sirve?")
        _tab_hasta(q, "#form-mensaje button[type=submit]")
        q.keyboard.press("Enter")
        q.locator("#historial .burbuja:has-text('¿Te sirve?')").wait_for()
        _tab_hasta(q, "#reportar")
        q.keyboard.press("Enter")
        q.wait_for_url("**/reportar")
        _tab_hasta(q, "#motivo-INAPPROPRIATE")  # en un grupo de radios, Tab entra al grupo y las flechas eligen
        q.keyboard.press("ArrowDown")
        q.keyboard.press("ArrowDown")
        assert q.is_checked("#motivo-SPAM")
        _tab_hasta(q, "#enviar")
        q.keyboard.press("Enter")
        q.locator("#mensajes .alert-success").wait_for()
        assert "Reporte registrado. Gracias por avisar" in q.inner_text("#mensajes")
    finally:
        autor.close()
        lector.close()
