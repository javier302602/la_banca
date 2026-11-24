"""Fase 3 en el navegador: ubicación en vivo entre dos personas, audio con reproductor y botón «Tomar foto»."""
import struct

from tests.e2e.navegador.conftest import iniciar_sesion, png, publicar, responder

UNAS = {"latitude": -9.2963, "longitude": -75.9981}


def wav() -> bytes:
    """WAV PCM de 0,1 s de silencio (8 kHz, 8 bits, mono)."""
    datos = b"\x80" * 800
    formato = struct.pack("<HHIIHH", 1, 1, 8000, 8000, 1, 8)
    return (b"RIFF" + struct.pack("<I", 36 + len(datos)) + b"WAVEfmt " + struct.pack("<I", 16) + formato
            + b"data" + struct.pack("<I", len(datos)) + datos)


def _chat(caro, ana):
    publicacion = publicar(caro, "Grupo de música")
    return publicacion, responder(ana, publicacion, "Hola, me uno")


def test_ubicacion_en_vivo_y_audio(navegador, servidor, usuarios, tmp_path):
    caro = navegador.new_context(base_url=servidor, locale="es-PE", timezone_id="America/Lima")
    ana = navegador.new_context(base_url=servidor, locale="es-PE", timezone_id="America/Lima",
                                geolocation=UNAS, permissions=["geolocation"])
    try:
        iniciar_sesion(caro, "caro@unas.edu.pe")
        iniciar_sesion(ana, "ana@unas.edu.pe")
        publicacion, chat = _chat(caro, ana)

        p_caro, p_ana = caro.new_page(), ana.new_page()
        p_caro.goto(f"/chats/{chat}")
        p_ana.goto(f"/chats/{chat}")
        boton = p_ana.locator("#boton-ubicacion")
        boton.wait_for(state="visible")  # aparece cuando el WebSocket está conectado

        # Compartir: se confirma, el botón cambia y la otra persona ve la ubicación con enlace al mapa
        p_ana.once("dialog", lambda d: d.accept())
        boton.click()
        p_ana.locator("#boton-ubicacion[aria-pressed='true']").wait_for()
        panel = p_caro.locator("#panel-ubicacion:has-text('ana_07 comparte su ubicación')")
        panel.wait_for(timeout=15_000)
        assert "mlat=-9.2963" in panel.locator("a").get_attribute("href")

        # Dejar de compartir: la otra persona deja de verla
        boton.click()
        p_caro.locator("#mensajes:has-text('dejó de compartir')").wait_for(timeout=15_000)
        assert p_caro.locator("#panel-ubicacion").is_hidden()

        # Audio: se adjunta, se envía y aparece con reproductor y enlace de descarga
        archivo = tmp_path / "nota de voz.wav"
        archivo.write_bytes(wav())
        p_ana.set_input_files("#audio", str(archivo))
        p_ana.locator("#adjunto-elegido:has-text('nota de voz.wav')").wait_for()
        p_ana.click("#form-mensaje button[type=submit]")
        burbuja = p_caro.locator("#historial .adjunto-audio").last
        burbuja.wait_for(timeout=15_000)
        assert burbuja.locator("audio").get_attribute("src").endswith("/documento")
        assert burbuja.locator("a[download='nota de voz.wav']").count() == 1
    finally:
        caro.request.post(f"/api/publicaciones/{publicacion}/cerrar")  # libera el cupo de publicaciones
        caro.close()
        ana.close()


def test_tomar_foto_deja_la_imagen_en_el_formulario(navegador, servidor, usuarios, tmp_path):
    """El diálogo de cámara se abre al instante y ofrece la cámara del sistema (selector nativo con capture).
    En headless no hay cámara real (Firefox incluso deja el permiso sin responder), así que se usa esa opción."""
    caro = navegador.new_context(base_url=servidor, locale="es-PE")
    ana = navegador.new_context(base_url=servidor, locale="es-PE")
    try:
        iniciar_sesion(caro, "caro@unas.edu.pe")
        iniciar_sesion(ana, "ana@unas.edu.pe")
        publicacion, chat = _chat(caro, ana)
        foto = tmp_path / "camara.png"
        foto.write_bytes(png())
        p = ana.new_page()
        p.goto(f"/chats/{chat}")
        p.locator("#historial .fila-mensaje").first.wait_for()
        con_camara = p.evaluate("!!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)")
        with p.expect_file_chooser(timeout=10_000) as selector:
            p.click("[data-tomar-foto='imagen']")
            if con_camara:  # diálogo propio: «Esperando el permiso…» o «No se pudo abrir…» + cámara del sistema
                dialogo = p.locator("dialog.dialogo-camara[open]")
                assert dialogo.locator("[role=status]").inner_text()
                dialogo.locator("[data-camara-sistema]").click()
            # sin getUserMedia (WebKit headless) se abre directamente el selector nativo
        selector.value.set_files(str(foto))
        assert p.locator("dialog.dialogo-camara").count() == 0
        p.locator("#adjunto-elegido:has-text('camara.png')").wait_for()
        p.click("#form-mensaje button[type=submit]")
        p.locator("#historial .burbuja.propia img").last.wait_for()
    finally:
        caro.request.post(f"/api/publicaciones/{publicacion}/cerrar")
        caro.close()
        ana.close()
