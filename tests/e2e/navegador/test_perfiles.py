"""Perfiles en el navegador (SRS v2.0, Fase 2): elegir avatar, biografía, foto y verlos en feed, detalle y chat."""
from PIL import Image

from tests.e2e.navegador.conftest import iniciar_sesion, publicar, responder


def _png(ruta):
    Image.new("RGB", (640, 480), (40, 160, 90)).save(ruta, format="PNG")
    return ruta


def test_editar_perfil_y_verlo_en_feed_detalle_y_chat(contexto, servidor, usuarios, tmp_path):
    iniciar_sesion(contexto, "ana@unas.edu.pe")
    p = contexto.new_page()
    p.goto("/perfil")
    p.locator("#vista-avatar[data-iniciales]").wait_for()
    assert p.locator("#vista-avatar").get_attribute("data-iniciales") == "A0"   # iniciales sobre un color
    assert "@unas.edu.pe" not in p.content()

    # Elegir un avatar (con teclado: el radio real es el control accesible) y escribir la biografía
    p.fill("#biografia", "Me gusta estudiar en la biblioteca")
    assert p.locator("#contador-biografia").inner_text().startswith("34")
    p.locator("#avatar-avatar-09").check()
    p.click("#form-perfil [type=submit]")
    p.locator("#mensajes-perfil .alert-success").wait_for()
    assert p.locator("#vista-avatar img").get_attribute("src") == "/static/avatares/avatar-09.svg"

    # Subir foto: se muestra en lugar del avatar y aparece «Quitar foto»
    p.set_input_files("#foto", str(_png(tmp_path / "yo.png")))
    assert p.locator("#nombre-foto").inner_text() == "yo.png"
    p.click("#form-foto [type=submit]")
    p.locator("#quitar-foto:not(.d-none)").wait_for()
    assert "/api/perfiles/ana_07/foto?v=" in p.locator("#vista-avatar img").get_attribute("src")

    # Al recargar se conserva lo elegido
    p.reload()
    p.locator("#vista-avatar img").wait_for()
    assert p.locator("#avatar-avatar-09").is_checked()
    assert p.input_value("#biografia") == "Me gusta estudiar en la biblioteca"

    # Otra persona ve la foto en el feed, el detalle (con enlace al perfil) y el chat
    pid = publicar(contexto, "Préstamo de calculadora")
    otro = contexto.browser.new_context(base_url=servidor, locale="es-PE")
    try:
        iniciar_sesion(otro, "beto@unas.edu.pe")
        q = otro.new_page()
        q.goto("/feed")
        tarjeta = q.locator(f"a[href='/publicaciones/{pid}']")
        tarjeta.wait_for()
        assert "/api/perfiles/ana_07/foto" in tarjeta.locator(".avatar img").get_attribute("src")
        q.goto(f"/publicaciones/{pid}")
        enlace = q.locator("#autor a.autor")
        enlace.wait_for()
        assert enlace.inner_text().strip() == "ana_07"  # las iniciales no ensucian el nombre
        enlace.click()
        q.wait_for_url("**/perfiles/ana_07")
        q.locator("#perfil:not([hidden])").wait_for()
        assert q.locator("#perfil-biografia").inner_text() == "Me gusta estudiar en la biblioteca"
        assert "@unas.edu.pe" not in q.content()
        chat = responder(otro, pid)
        q.goto(f"/chats/{chat}")
        q.locator("#contraparte .avatar img").wait_for()
        q.goto("/chats")
        q.locator("#lista a .avatar img").first.wait_for()
    finally:
        otro.close()

    # Quitar la foto vuelve al avatar elegido; el foco pasa al selector de archivo
    p.click("#quitar-foto")
    p.locator("#quitar-foto.d-none").wait_for(state="attached")
    assert p.locator("#vista-avatar img").get_attribute("src") == "/static/avatares/avatar-09.svg"
    assert p.evaluate("document.activeElement.id") == "foto"

    # Volver a las iniciales
    p.locator("#avatar-ninguno").check()
    p.click("#form-perfil [type=submit]")
    p.locator("#vista-avatar[data-iniciales]").wait_for()


def test_foto_invalida_muestra_el_error_junto_al_campo(contexto, usuarios, tmp_path):
    iniciar_sesion(contexto, "caro@unas.edu.pe")
    p = contexto.new_page()
    p.goto("/perfil")
    p.locator("#vista-avatar[data-iniciales]").wait_for()
    falsa = tmp_path / "foto.png"
    falsa.write_bytes(b"MZ\x90\x00 esto no es una imagen")
    p.set_input_files("#foto", str(falsa))
    p.click("#form-foto [type=submit]")
    error = p.locator("#foto[aria-invalid=true]")
    error.wait_for()
    assert "JPG, PNG o WebP" in p.locator("#form-foto").inner_text()


def test_perfil_inexistente(contexto, usuarios):
    iniciar_sesion(contexto, "ana@unas.edu.pe")
    p = contexto.new_page()
    p.goto("/perfiles/nadie_aqui")
    p.locator("#mensajes .alert").wait_for()
    assert "no existe" in p.locator("#mensajes").inner_text()
    assert p.locator("#perfil").is_hidden()
