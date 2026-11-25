"""Fase 4 en el navegador: videollamada real con WebRTC entre dos personas (Chromium con cámara y micrófono
simulados), chat de la llamada, silenciar, siguiente/colgar y reporte; más la portada en los tres navegadores."""
import pytest

from tests.e2e.navegador.conftest import iniciar_sesion

MEDIOS_FALSOS = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]


def _con_identidad(contexto, correo, nombre, carrera):
    iniciar_sesion(contexto, correo)
    r = contexto.request.patch("/api/cuentas/me/identidad", data={"nombre": nombre, "carrera": carrera})
    assert r.ok, r.text()


def test_portada_explica_y_exige_nombre_y_carrera(navegador, servidor, usuarios, base_navegador):
    db, _ = base_navegador
    db.accounts.update_one({"email": "caro@unas.edu.pe"}, {"$unset": {"fullName": "", "career": ""}})
    contexto = navegador.new_context(base_url=servidor, locale="es-PE")
    try:
        iniciar_sesion(contexto, "caro@unas.edu.pe")
        p = contexto.new_page()
        assert contexto.request.patch("/api/cuentas/me/identidad", data={"nombre": "", "carrera": ""}).status == 422
        p.goto("/videollamada")
        assert p.locator(".lista-pasos li").count() == 3
        assert "No compartas datos personales" in p.locator(".reglas-llamada").inner_text()
        assert p.locator("#falta-perfil a[href='/perfil']").is_visible() and p.locator("#empezar").count() == 0
        p.goto("/perfil")
        p.fill("#nombre", "Caro Luna")
        p.select_option("#carrera", "Zootecnia")
        p.click("#form-identidad button[type=submit]")
        p.locator("#mensajes-perfil .alert-success").wait_for()
        p.goto("/videollamada")
        assert p.locator("#empezar").is_visible()
    finally:
        contexto.close()


def test_videollamada_webrtc_entre_dos_personas(playwright_sync, navegador, servidor, usuarios):
    if navegador.browser_type.name != "chromium":  # usa su propio Chromium con cámara simulada: basta una vez
        pytest.skip("WebRTC con medios simulados se prueba una vez, en Chromium")
    navegador = playwright_sync.chromium.launch(args=MEDIOS_FALSOS)
    ana = navegador.new_context(base_url=servidor, locale="es-PE", permissions=["camera", "microphone"])
    beto = navegador.new_context(base_url=servidor, locale="es-PE", permissions=["camera", "microphone"])
    try:
        _con_identidad(ana, "ana@unas.edu.pe", "Ana Ríos", "Ingeniería en Informática y Sistemas")
        _con_identidad(beto, "beto@unas.edu.pe", "Beto Paz", "Agronomía")
        pa, pb = ana.new_page(), beto.new_page()
        for p in (pa, pb):
            p.goto("/videollamada")
            p.click("#empezar")
            p.locator("#llamada:not([hidden])").wait_for()

        # Emparejados: cada uno ve el nombre y la carrera del otro y recibe video de verdad (WebRTC)
        pa.locator("#pareja-nombre:has-text('Beto Paz')").wait_for(timeout=20_000)
        pb.locator("#pareja-nombre:has-text('Ana Ríos')").wait_for(timeout=20_000)
        assert pa.locator("#pareja-carrera").inner_text() == "Agronomía"
        for p in (pa, pb):
            p.wait_for_function("document.getElementById('video-remoto').videoWidth > 0", timeout=20_000)
            p.locator("#estado-llamada[hidden]").wait_for(state="attached", timeout=20_000)

        # Chat de la llamada
        pa.fill("#texto-llamada", "¡Hola, Beto!")
        pa.click("#form-chat-llamada button[type=submit]")
        pb.locator("#historial-llamada:has-text('¡Hola, Beto!')").wait_for()

        # Silenciar y apagar la cámara cambian el estado del botón (y apagan la pista)
        pa.click("#boton-microfono")
        assert pa.locator("#boton-microfono").get_attribute("aria-pressed") == "true"
        assert pa.evaluate("document.getElementById('video-propio').srcObject.getAudioTracks()[0].enabled") is False
        pa.click("#boton-camara")
        assert pa.locator("#boton-camara").get_attribute("aria-pressed") == "true"

        # Reportar: se guarda y se pasa a otra persona
        pb.click("#boton-reportar")
        pb.check("#motivo-INSULTOS")
        pb.fill("#detalle-reporte", "Prueba de reporte")
        pb.click("#form-reporte button[type=submit]")
        pb.locator("#mensajes .alert-success:has-text('Reporte enviado')").wait_for()
        pa.locator("#estado-llamada:has-text('La otra persona salió')").wait_for(timeout=10_000)

        # Colgar: vuelve a la portada y apaga la cámara
        pa.click("#boton-colgar")
        pa.locator("#inicio-llamada:not([hidden])").wait_for()
        assert pa.evaluate("document.getElementById('video-propio').srcObject") is None
    finally:
        ana.close()
        beto.close()
        navegador.close()
