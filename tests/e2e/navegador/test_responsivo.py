"""Diseño responsivo mobile-first en los anchos de diseño 360, 768 y 1024 px."""
import pytest

from tests.e2e.navegador.conftest import iniciar_sesion, publicar, responder
from tests.e2e.navegador.test_wcag22 import todas

ANCHOS = (360, 768, 1024)


@pytest.fixture(scope="module")
def escenario(navegador, servidor, usuarios):
    autor, lector = navegador.new_context(base_url=servidor), navegador.new_context(base_url=servidor)
    try:
        iniciar_sesion(autor, "beto@unas.edu.pe")
        iniciar_sesion(lector, "ana@unas.edu.pe")
        pid = publicar(autor, "Busco grupo de estudio", "NECESITO")
        publicar(autor, "Presto apuntes", "OFREZCO")
        publicar(autor, "Partido de vóley", "ACTIVIDAD")
        chat = responder(lector, pid, "Me apunto")
        publicar(lector, "Ofrezco clases de cálculo", "OFREZCO")
        return {"pid": pid, "chat": chat}
    finally:
        autor.close()
        lector.close()


def _pagina(navegador, servidor, ancho, correo=None):
    contexto = navegador.new_context(base_url=servidor, viewport={"width": ancho, "height": 800})
    if correo:
        iniciar_sesion(contexto, correo)
    return contexto, contexto.new_page()


@pytest.mark.parametrize("ancho,columnas", [(360, 1), (768, 2), (1024, 3)])
def test_feed_en_1_2_y_3_columnas(navegador, servidor, escenario, ancho, columnas):
    contexto, p = _pagina(navegador, servidor, ancho, "ana@unas.edu.pe")
    try:
        p.goto("/feed")
        p.locator(".tarjeta-publicacion").nth(2).wait_for()
        xs = {round(p.locator(".tarjeta-publicacion").nth(i).bounding_box()["x"]) for i in range(3)}
        assert len(xs) == columnas, xs
    finally:
        contexto.close()


@pytest.mark.parametrize("ancho", ANCHOS)
def test_sin_desplazamiento_horizontal_en_ningun_ancho(navegador, servidor, escenario, ancho):
    desbordes = []
    for ruta, correo, listo in todas(escenario):
        contexto, p = _pagina(navegador, servidor, ancho, correo)
        try:
            p.goto(ruta)
            p.locator(listo).first.wait_for()
            if p.evaluate("Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > innerWidth"):
                desbordes.append(ruta)
        finally:
            contexto.close()
    assert not desbordes, desbordes


@pytest.mark.parametrize("ancho,colapsado,titulo_px,formulario_max", [
    (360, True, 20, None), (768, False, 24, 480), (1024, False, 24, 480)])
def test_menu_titulos_y_contenedores_por_ancho(navegador, servidor, usuarios, ancho, colapsado, titulo_px,
                                               formulario_max):
    contexto, p = _pagina(navegador, servidor, ancho)
    try:
        p.goto("/login")
        assert p.locator(".navbar-toggler").is_visible() is colapsado
        assert p.locator("#nav-principal a[href='/registro']").is_visible() is not colapsado
        assert p.locator("main h1").evaluate("n => parseFloat(getComputedStyle(n).fontSize)") == titulo_px
        formulario = p.locator(".contenedor-estrecho").bounding_box()["width"]
        principal = p.locator("main").evaluate("n => n.clientWidth - parseFloat(getComputedStyle(n).paddingLeft)"
                                               " - parseFloat(getComputedStyle(n).paddingRight)")
        if formulario_max is None:
            assert abs(formulario - principal) < 1  # a 360 px ocupa todo el ancho disponible
        else:
            assert formulario <= formulario_max  # 30 rem
    finally:
        contexto.close()
