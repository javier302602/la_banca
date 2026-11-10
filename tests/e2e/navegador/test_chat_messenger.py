"""Chat estilo Messenger en el navegador (SRS v2.0, Fase 4): burbujas agrupadas con avatar, enviado/visto,
emojis, stickers y documentos."""
import io
import zipfile

from tests.e2e.navegador.conftest import iniciar_sesion, publicar, responder

PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def docx() -> bytes:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        zf.writestr("[Content_Types].xml", '<Types><Override PartName="/word/document.xml" ContentType="application/'
                                           'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        zf.writestr("word/document.xml", "<w/>")
    return salida.getvalue()


def test_chat_messenger(navegador, servidor, usuarios, tmp_path):
    beto, ana = navegador.new_context(base_url=servidor, locale="es-PE"), navegador.new_context(base_url=servidor, locale="es-PE")
    try:
        iniciar_sesion(beto, "beto@unas.edu.pe")
        iniciar_sesion(ana, "ana@unas.edu.pe")
        assert beto.request.patch("/api/cuentas/me/perfil", data={"avatar": "avatar-04"}).ok
        chat = responder(ana, publicar(beto, "Préstamo de libro de física"), "Hola, ¿sigue disponible?")
        for texto in ("Sí, todavía lo tengo", "¿Cuándo lo necesitas?"):
            assert beto.request.post(f"/api/chats/{chat}/mensajes", multipart={"texto": texto}).ok

        p = ana.new_page()
        p.goto(f"/chats/{chat}")
        filas = p.locator("#historial .fila-mensaje")
        filas.nth(2).wait_for()
        # Agrupación por autor: el avatar de beto solo junto al último mensaje de su grupo
        assert filas.nth(1).locator(".avatar").get_attribute("class").endswith("oculto")
        assert filas.nth(2).locator(".avatar img").get_attribute("src") == "/static/avatares/avatar-04.svg"
        assert "continua" in filas.nth(2).get_attribute("class") and "continua" not in filas.nth(1).get_attribute("class")
        assert "Visto" in filas.nth(0).inner_text()  # beto ya escribió después: leyó el «Hola»

        # Enviado → Visto cuando la otra persona abre el chat (lastReadAt)
        p.fill("#texto", "Mañana a las 10")
        p.click("#form-mensaje [type=submit]")
        propia = p.locator("#historial .fila-mensaje.propia", has_text="Mañana a las 10")
        propia.wait_for()
        assert "Enviado" in propia.inner_text()
        assert beto.request.get(f"/api/chats/{chat}").ok
        propia.locator(".estado-mensaje:has-text('Visto')").wait_for(timeout=5000)

        # Emojis: el panel se abre con el foco en el primer emoji; Escape lo cierra y devuelve el foco
        p.click("#boton-emojis")
        assert p.get_attribute("#boton-emojis", "aria-expanded") == "true"
        assert p.evaluate("document.activeElement.closest('#panel-emojis') !== null")
        p.locator("#panel-emojis button", has_text="👍").click()
        assert p.input_value("#texto") == "👍"
        p.locator("#panel-emojis button").first.focus()
        p.keyboard.press("Escape")
        assert p.locator("#panel-emojis").is_hidden() and p.evaluate("document.activeElement.id") == "boton-emojis"
        p.click("#form-mensaje [type=submit]")
        p.locator("#historial .burbuja.propia:has-text('👍')").wait_for()

        # Sticker: se envía al elegirlo y se ve sin fondo de burbuja, con su nombre como texto alternativo
        p.click("#boton-stickers")
        p.get_by_role("button", name="Pulgar arriba").click()
        sticker = p.locator("#historial .burbuja.sticker img[alt='Pulgar arriba']")
        sticker.wait_for()
        assert sticker.get_attribute("src") == "/static/stickers/sticker-17.svg"
        assert p.locator("#panel-stickers").is_hidden()

        # Documento: tarjeta con icono, nombre y tamaño; descarga como adjunto con nosniff
        ruta = tmp_path / "Guía de estudio.pdf"
        ruta.write_bytes(PDF)
        p.set_input_files("#documento", str(ruta))
        assert "Guía de estudio.pdf" in p.locator("#adjunto-elegido").inner_text()
        p.click("#form-mensaje [type=submit]")
        tarjeta = p.locator("#historial a.tarjeta-documento", has_text="Guía de estudio.pdf")
        tarjeta.wait_for()
        assert tarjeta.locator(".bi-file-earmark-pdf").count() == 1
        assert tarjeta.locator(".tamano-documento").inner_text().endswith("B")
        r = ana.request.get(tarjeta.get_attribute("href"))
        assert r.ok and r.body() == PDF
        assert r.headers["content-disposition"].startswith("attachment;")
        assert r.headers["x-content-type-options"] == "nosniff"
        with p.expect_download() as descarga:
            tarjeta.click()
        assert descarga.value.suggested_filename == "Guía de estudio.pdf"
        # Beto (el otro participante) recibe la tarjeta por sondeo; un tercero no puede descargarla
        q = beto.new_page()
        q.goto(f"/chats/{chat}")
        q.locator("#historial a.tarjeta-documento").wait_for()
        caro = navegador.new_context(base_url=servidor)
        try:
            iniciar_sesion(caro, "caro@unas.edu.pe")
            assert caro.request.get(tarjeta.get_attribute("href")).status == 404
        finally:
            caro.close()

        # DOCX enviado como .doc: se acepta por contenido y se nombra .docx
        ruta = tmp_path / "apuntes.doc"
        ruta.write_bytes(docx())
        p.set_input_files("#documento", str(ruta))
        p.click("#form-mensaje [type=submit]")
        p.locator("#historial a.tarjeta-documento", has_text="apuntes.docx").wait_for()

        # Ejecutable renombrado: error junto a la barra de adjuntos, enlazado al campo
        ruta = tmp_path / "tarea.pdf"
        ruta.write_bytes(b"MZ\x90\x00" + b"\x00" * 200)
        p.set_input_files("#documento", str(ruta))
        p.click("#form-mensaje [type=submit]")
        p.locator("#error-documento").wait_for()
        assert p.locator("#error-documento").inner_text() == "No se permiten archivos ejecutables"
        assert p.get_attribute("#documento", "aria-invalid") == "true"
        assert "error-documento" in p.get_attribute("#documento", "aria-describedby")
        # Texto y adjunto a la vez: se pide uno solo
        p.fill("#texto", "y además esto")
        p.click("#form-mensaje [type=submit]")
        assert "solo uno" in p.locator("#form-mensaje").inner_text()
        p.get_by_role("button", name="Quitar adjunto").click()
        assert p.locator("#adjunto-elegido").is_hidden()
    finally:
        beto.close()
        ana.close()
