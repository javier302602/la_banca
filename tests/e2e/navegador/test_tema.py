"""Modo claro y oscuro (cambio 1.3): respeta prefers-color-scheme, el interruptor alterna y recuerda la elección."""
import pytest


@pytest.mark.parametrize("sistema,esperado", [("light", "light"), ("dark", "dark")])
def test_respeta_la_preferencia_del_sistema(navegador, servidor, sistema, esperado):
    contexto = navegador.new_context(base_url=servidor, color_scheme=sistema)
    try:
        p = contexto.new_page()
        p.goto("/login")
        assert p.evaluate("document.documentElement.dataset.bsTheme") == esperado
        assert p.get_attribute("#boton-tema", "aria-checked") == str(esperado == "dark").lower()
    finally:
        contexto.close()


def test_interruptor_alterna_y_recuerda(navegador, servidor):
    contexto = navegador.new_context(base_url=servidor, color_scheme="light")
    try:
        p = contexto.new_page()
        p.goto("/login")
        boton = p.locator("#boton-tema")
        assert boton.get_attribute("role") == "switch" and boton.get_attribute("aria-label") == "Modo oscuro"
        fondo_claro = p.evaluate("getComputedStyle(document.body).backgroundColor")
        boton.focus()
        p.keyboard.press("Enter")  # accesible con teclado
        assert p.evaluate("document.documentElement.dataset.bsTheme") == "dark"
        assert boton.get_attribute("aria-checked") == "true"
        assert p.evaluate("getComputedStyle(document.body).backgroundColor") != fondo_claro
        p.goto("/registro")  # otra página y recarga: recuerda la elección aunque el sistema esté en claro
        assert p.evaluate("document.documentElement.dataset.bsTheme") == "dark"
        assert p.evaluate("localStorage.getItem('banca.tema')") == "oscuro"
        p.click("#boton-tema")
        p.reload()
        assert p.evaluate("document.documentElement.dataset.bsTheme") == "light"
    finally:
        contexto.close()
