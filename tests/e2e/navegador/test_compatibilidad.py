"""RNF-COM-01: los flujos principales (registro, inicio de sesión, publicar, responder, chatear y reportar) se
completan en cada motor: Chromium (Chrome y Edge), Firefox y WebKit (Safari). En Chromium y WebKit también con
emulación de móvil (Chrome en Android → Pixel 7; Safari en iOS → iPhone 14). Firefox no admite emulación de móvil.
"""
import re
import uuid

import pytest

from tests.e2e.navegador.conftest import CLAVE, iniciar_sesion, ultimo_enlace

DISPOSITIVOS = {"chromium": "Pixel 7", "webkit": "iPhone 14"}


@pytest.fixture(params=["escritorio", "movil"])
def perfil(request, navegador, playwright_sync):
    motor = navegador.browser_type.name
    if request.param == "escritorio":
        return {"viewport": {"width": 1366, "height": 900}}
    if motor not in DISPOSITIVOS:
        pytest.skip(f"{motor} no admite emulación de dispositivos móviles")
    return dict(playwright_sync.devices[DISPOSITIVOS[motor]])


def _pulsar(pagina, selector, movil):
    destino = pagina.locator(selector).first
    destino.tap() if movil else destino.click()


def _menu(pagina, enlace, movil):
    if movil:  # en móvil el menú está colapsado
        _pulsar(pagina, ".navbar-toggler", movil)
    _pulsar(pagina, f"#nav-principal a:has-text('{enlace}')", movil)


def test_flujos_principales(navegador, servidor, usuarios, registro_servidor, perfil):
    movil = perfil.get("is_mobile", False)
    nick = f"u{uuid.uuid4().hex[:8]}"
    correo = f"{nick}@unas.edu.pe"
    nuevo = navegador.new_context(base_url=servidor, **perfil)
    autor = navegador.new_context(base_url=servidor, **perfil)
    try:
        # Registro + activación por enlace + inicio de sesión
        p = nuevo.new_page()
        p.goto("/registro")
        p.fill("#correo", correo)
        p.fill("#nickname", nick)
        p.fill("#contrasena", CLAVE)
        p.fill("#confirmacion", CLAVE)
        _pulsar(p, "#acepta_terminos", movil)  # la etiqueta contiene el enlace a /terminos
        _pulsar(p, "#form-registro button[type=submit]", movil)
        p.locator("#mensajes .alert-success:has-text('Revisa tu correo para activar tu cuenta')").wait_for()
        p.goto(ultimo_enlace(registro_servidor, "/activar"))
        p.locator("#mensajes:has-text('Activación de cuenta exitosa')").wait_for()
        _pulsar(p, "#continuar a", movil)
        p.wait_for_url("**/login")
        p.fill("#correo", correo)
        p.fill("#contrasena", CLAVE)
        _pulsar(p, "#form-login button[type=submit]", movil)
        p.wait_for_url("**/feed")

        # Publicar
        _menu(p, "Publicar", movil)
        p.wait_for_url("**/publicaciones/nueva")
        _pulsar(p, "label[for=tipo-OFREZCO]", movil)
        p.fill("#titulo", f"Ofrezco apuntes ({nick})")
        p.fill("#descripcion", "De Diseño Detallado, para fotocopiar")
        _pulsar(p, "#form-publicacion button[type=submit]", movil)
        p.wait_for_url(re.compile(r"/publicaciones/[0-9a-f]{24}$"))
        publicacion = p.url.rsplit("/", 1)[1]

        # Otro usuario responde desde el feed, chatea y reporta
        iniciar_sesion(autor, "beto@unas.edu.pe")
        q = autor.new_page()
        q.goto("/feed")
        _pulsar(q, f"a[href='/publicaciones/{publicacion}']", movil)
        q.wait_for_url(f"**/publicaciones/{publicacion}")
        _pulsar(q, "#acciones a:has-text('Responder')", movil)
        q.fill("#texto", "Me interesan, ¿dónde te encuentro?")
        _pulsar(q, "#form-mensaje button[type=submit]", movil)
        q.wait_for_url(re.compile(r"/chats/[0-9a-f]{24}$"))
        q.locator("#historial .burbuja").first.wait_for()

        # El autor recibe el mensaje sin recargar y contesta
        _menu(p, "Mis chats", movil)
        _pulsar(p, "#lista a", movil)
        p.locator("#historial .burbuja:has-text('dónde te encuentro')").wait_for()
        p.fill("#texto", "En la banca del pabellón central")
        _pulsar(p, "#form-mensaje button[type=submit]", movil)
        q.locator("#historial .burbuja:has-text('pabellón central')").wait_for()  # recibido por sondeo

        _pulsar(q, "#reportar", movil)
        q.wait_for_url("**/reportar")
        _pulsar(q, "label[for=motivo-SPAM]", movil)
        _pulsar(q, "#enviar", movil)
        q.locator("#mensajes .alert-success:has-text('Reporte registrado. Gracias por avisar')").wait_for()
    finally:
        nuevo.close()
        autor.close()
