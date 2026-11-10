"""Imágenes en publicaciones en el navegador (SRS v2.0, Fase 3): elegir hasta 3, compresión en el navegador,
miniatura en el feed y galería en el detalle."""
import os

from PIL import Image

from tests.e2e.navegador.conftest import iniciar_sesion


def _png(ruta, color, tamano=(400, 300)):
    Image.new("RGB", tamano, color).save(ruta, format="PNG")
    return str(ruta)


def _ruido(ruta, lado=1800):
    """PNG de ruido: no se comprime, pesa más de 5 MB y obliga a reducirlo en el navegador."""
    Image.frombytes("RGB", (lado, lado), os.urandom(lado * lado * 3)).save(ruta, format="PNG")
    assert os.path.getsize(ruta) > 5 * 1024 * 1024
    return str(ruta)


def test_publicar_con_imagenes_y_ver_la_galeria(contexto, usuarios, tmp_path):
    iniciar_sesion(contexto, "ana@unas.edu.pe")
    p = contexto.new_page()
    p.goto("/publicaciones/nueva")
    p.locator("#cupo:has-text('Publicaciones activas')").wait_for()
    p.locator("label[for=tipo-OFREZCO]").click()
    p.fill("#titulo", "Vendo calculadora científica")
    p.fill("#descripcion", "Casi nueva, con estuche")

    # Dos imágenes y luego dos más: se conservan 3 y se avisa junto al campo
    p.set_input_files("#imagenes", [_png(tmp_path / "a.png", "red"), _png(tmp_path / "b.png", "green")])
    assert p.locator("#vista-previa li").count() == 2
    p.set_input_files("#imagenes", [_ruido(tmp_path / "grande.png"), _png(tmp_path / "d.png", "blue")])
    assert p.locator("#vista-previa li").count() == 3
    assert "hasta 3 imágenes" in p.locator("#form-publicacion").inner_text()
    assert p.locator("#nombre-imagenes").inner_text() == "3 de 3 imágenes elegidas"

    # Quitar una con su botón (nombre accesible con el nombre del archivo)
    p.get_by_role("button", name="Quitar a.png").click()
    assert p.locator("#vista-previa li").count() == 2
    assert p.evaluate("document.activeElement.id") == "imagenes"

    p.click("#form-publicacion [type=submit]")
    p.wait_for_url("**/publicaciones/*", timeout=30_000)
    p.locator("#galeria:not([hidden])").wait_for()
    miniaturas = p.locator("#galeria-miniaturas button")
    assert miniaturas.count() == 2
    assert miniaturas.nth(0).get_attribute("aria-current") == "true"
    grande = p.locator("#galeria-imagen")
    assert "Imagen 1 de 2" in grande.get_attribute("alt")
    miniaturas.nth(1).click()
    assert miniaturas.nth(1).get_attribute("aria-current") == "true"
    assert "Imagen 2 de 2" in grande.get_attribute("alt") and grande.get_attribute("src").endswith("/imagenes/1")
    p.wait_for_function("document.getElementById('galeria-imagen').naturalWidth > 0")
    # La imagen de ruido se redujo en el navegador antes de subirla (el servidor acepta ≤ 5 MB)
    ancho = p.evaluate("document.getElementById('galeria-imagen').naturalWidth")
    assert 0 < ancho <= 1800

    # Feed: miniatura y cantidad
    p.goto("/feed")
    tarjeta = p.locator(".tarjeta-publicacion", has_text="Vendo calculadora científica")
    tarjeta.wait_for()
    assert tarjeta.locator("img.miniatura-publicacion").count() == 1
    assert "2 imágenes" in tarjeta.inner_text()


def test_publicar_sin_imagenes_sigue_igual(contexto, usuarios):
    iniciar_sesion(contexto, "beto@unas.edu.pe")
    p = contexto.new_page()
    p.goto("/publicaciones/nueva")
    p.locator("#cupo:has-text('Publicaciones activas')").wait_for()
    p.locator("label[for=tipo-NECESITO]").click()
    p.fill("#titulo", "Busco apuntes")
    p.fill("#descripcion", "De química")
    p.click("#form-publicacion [type=submit]")
    p.wait_for_url("**/publicaciones/*")
    p.locator("#detalle:not(.d-none)").wait_for()
    assert p.locator("#galeria").is_hidden()
