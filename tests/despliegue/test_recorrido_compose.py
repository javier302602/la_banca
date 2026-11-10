"""Fase 7 — recorrido completo en el navegador contra un docker compose levantado con datos de demo.

    docker compose up -d && docker compose exec app python -m scripts.seed_demo --reiniciar
    PRUEBA_COMPOSE_URL=https://localhost:8443 PRUEBA_MAILPIT_URL=http://localhost:8025 pytest tests/despliegue/test_recorrido_compose.py

Guarda capturas en docs/demo/. Solo corre con PRUEBA_COMPOSE_URL.
"""
import os
import re
import secrets
from pathlib import Path

import pytest

URL = os.environ.get("PRUEBA_COMPOSE_URL", "")
MAILPIT = os.environ.get("PRUEBA_MAILPIT_URL", "")
CAPTURAS = Path(__file__).resolve().parents[2] / "docs" / "demo"
CLAVE = os.environ.get("DEMO_CONTRASENA", "Demo1234!")

pytestmark = pytest.mark.skipif(not URL, reason="solo con PRUEBA_COMPOSE_URL")


@pytest.fixture(scope="module")
def navegador():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def contexto(navegador, **kw):
    ctx = navegador.new_context(base_url=URL, ignore_https_errors=True, locale="es-PE", timezone_id="America/Lima",
                                viewport={"width": 1280, "height": 860}, **kw)
    ctx.set_default_timeout(15_000)
    return ctx


def captura(pagina, nombre):
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    pagina.screenshot(path=str(CAPTURAS / f"{nombre}.png"), full_page=True)


def entrar(pagina, correo):
    pagina.goto("/login")
    pagina.fill("#correo", correo)
    pagina.fill("#contrasena", CLAVE)
    pagina.click("#form-login [type=submit]")
    pagina.wait_for_url("**/feed")


def test_recorrido_completo(navegador, tmp_path):
    ctx = contexto(navegador)
    p = ctx.new_page()
    try:
        p.goto("/")
        assert re.search(r"Versión \d+\.\d+\.\d+", p.locator("#version-app").inner_text())
        captura(p, "01-portada")

        entrar(p, "ana.demo@unas.edu.pe")
        tarjetas = p.locator(".tarjeta-publicacion")
        tarjetas.nth(3).wait_for()
        assert tarjetas.count() >= 4 and p.locator(".tarjeta-publicacion img.miniatura-publicacion").count() >= 3
        assert p.locator(".tarjeta-publicacion .avatar img[src^='/static/avatares/']").count() >= 3
        captura(p, "02-feed")

        p.locator(".tarjeta-publicacion", has_text="Grupo de estudio de derivadas").click()
        p.locator("#galeria:not([hidden])").wait_for()
        assert p.locator("#galeria-miniaturas button").count() == 3
        p.locator("#galeria-miniaturas button").nth(2).click()
        captura(p, "03-detalle-galeria")

        p.goto("/chats")
        p.locator("#lista a").nth(1).wait_for()
        captura(p, "04-mis-chats")
        p.locator("#lista a", has_text="caro_demo").click()
        p.locator("#historial .fila-mensaje").nth(5).wait_for()
        assert p.locator("#historial .burbuja.sticker img[alt='Cara enamorada']").count() == 1
        tarjeta = p.locator("#historial a.tarjeta-documento", has_text="Resumen capítulo 3.pdf")
        assert tarjeta.locator(".bi-file-earmark-pdf").count() == 1
        with p.expect_download() as descarga:
            tarjeta.click()
        assert descarga.value.suggested_filename == "Resumen capítulo 3.pdf"
        assert (descarga.value.path().read_bytes()[:5]) == b"%PDF-"
        # Emoji + sticker desde la interfaz
        p.click("#boton-emojis")
        p.locator("#panel-emojis button", has_text="🎉").click()
        p.click("#form-mensaje [type=submit]")
        p.locator("#historial .burbuja.propia:has-text('🎉')").wait_for()
        p.click("#boton-stickers")
        p.get_by_role("button", name="Estrella").click()
        p.locator("#historial .burbuja.sticker img[alt='Estrella']").wait_for()
        captura(p, "05-chat")

        # Caro abre el chat: Ana ve «Visto»
        otra = contexto(navegador)
        q = otra.new_page()
        entrar(q, "caro.demo@unas.edu.pe")
        q.goto(p.url.replace(URL, ""))
        q.locator("#historial .burbuja.sticker img[alt='Estrella']").wait_for()
        p.locator("#historial .fila-mensaje.propia").last.locator(".estado-mensaje:has-text('Visto')").wait_for()
        otra.close()

        # Perfil propio y público, en modo oscuro
        p.goto("/perfil")
        p.locator("#vista-avatar img").wait_for()
        assert p.locator("#avatar-avatar-06").is_checked()
        p.click("#boton-tema")
        assert p.evaluate("document.documentElement.dataset.bsTheme") == "dark"
        p.mouse.move(0, 0)
        p.wait_for_timeout(400)  # las transiciones de color de Bootstrap (0,15 s) terminan antes de la captura
        captura(p, "06-perfil-oscuro")
        p.goto("/perfiles/caro_demo")
        p.locator("#perfil:not([hidden])").wait_for()
        assert "enseñar cálculo" in p.locator("#perfil-biografia").inner_text() and "@unas.edu.pe" not in p.content()
        captura(p, "07-perfil-publico-oscuro")
        p.click("#boton-tema")

        # Publicar con imagen desde la interfaz (Dani tiene cupo)
        p.click("[data-cerrar-sesion]")
        p.wait_for_url(re.compile(r".*/(login|)$"))
        entrar(p, "dani.demo@unas.edu.pe")
        p.goto("/publicaciones/nueva")
        p.locator("label[for=tipo-OFREZCO]").click()
        p.fill("#titulo", "Regalo plantas de la feria")
        p.fill("#descripcion", "Tengo 3 macetas pequeñas")
        from PIL import Image

        Image.new("RGB", (640, 480), (47, 158, 99)).save(tmp_path / "planta.png")
        p.set_input_files("#imagenes", str(tmp_path / "planta.png"))
        p.click("#form-publicacion [type=submit]")
        p.locator("#galeria:not([hidden])").wait_for()
    finally:
        ctx.close()


@pytest.mark.skipif(not MAILPIT, reason="solo con PRUEBA_MAILPIT_URL (perfil dev)")
def test_registro_con_correo_en_mailpit(navegador):
    import httpx

    nick = f"nuevo_{secrets.token_hex(3)}"
    correo = f"{nick}@unas.edu.pe"
    ctx = contexto(navegador)
    p = ctx.new_page()
    try:
        p.goto("/registro")
        p.fill("#correo", correo)
        p.fill("#nickname", nick)
        p.fill("#contrasena", CLAVE)
        p.fill("#confirmacion", CLAVE)
        p.check("#acepta_terminos")
        p.click("#form-registro [type=submit]")
        p.locator("#mensajes .alert-success").wait_for()  # «revisa tu correo»
        with httpx.Client(timeout=10) as m:
            for _ in range(20):
                mensajes = m.get(f"{MAILPIT}/api/v1/search", params={"query": f"to:{correo}"}).json()["messages"]
                if mensajes:
                    break
                p.wait_for_timeout(500)
            texto = m.get(f"{MAILPIT}/api/v1/message/{mensajes[0]['ID']}").json()["Text"]
        enlace = re.search(r"https://\S+token=[\w-]+", texto).group(0)
        assert enlace.startswith(URL)
        p.goto(enlace.replace(URL, ""))
        p.locator("#mensajes .alert-success").wait_for()
        p.locator("#continuar:not(.d-none)").wait_for()
        entrar(p, correo)
    finally:
        ctx.close()
