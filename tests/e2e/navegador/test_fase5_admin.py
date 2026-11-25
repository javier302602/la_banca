"""Fase 5 en el navegador: el panel de administración muestra los reportes, aplica una advertencia que la
persona ve como aviso, y registra la acción en el historial. Quien no es admin no entra."""
from tests.e2e.navegador.conftest import iniciar_sesion, publicar


def test_panel_admin_advertencia_e_historial(navegador, servidor, usuarios):
    dani = navegador.new_context(base_url=servidor, locale="es-PE")   # administradora (ADMIN_EMAILS)
    ana = navegador.new_context(base_url=servidor, locale="es-PE")
    beto = navegador.new_context(base_url=servidor, locale="es-PE")
    try:
        for contexto, correo in ((dani, "dani@unas.edu.pe"), (ana, "ana@unas.edu.pe"), (beto, "beto@unas.edu.pe")):
            iniciar_sesion(contexto, correo)
        pid = publicar(ana, "Vendo apuntes de química")
        r = beto.request.post(f"/api/publicaciones/{pid}/reportes", data={"codigo_motivo": "SPAM", "observacion": "Publicidad"})
        assert r.ok, r.text()

        # Quien no es admin no ve el enlace ni entra al panel
        pa = ana.new_page()
        pa.goto("/feed")
        assert pa.locator("#nav-admin").count() == 0
        pa.goto("/admin")
        pa.wait_for_url("**/feed")

        # La admin ve el contador del menú y el reporte con quién reportó y a quién
        p = dani.new_page()
        p.goto("/admin")
        p.locator("#nav-reportes:not(.d-none)").wait_for()
        tarjeta = p.locator(".tarjeta-reporte", has_text="Vendo apuntes de química").first
        tarjeta.wait_for()
        texto = tarjeta.inner_text()
        assert "@beto_9" in texto and "@ana_07" in texto and "Spam" in texto and "Publicidad" in texto

        # Advertir: se confirma en un diálogo y la persona ve el aviso hasta marcarlo como leído
        tarjeta.get_by_role("button", name="Advertir").click()
        p.fill("#mensaje-accion", "No publiques avisos comerciales")
        p.click("#confirmar-accion")
        p.locator("#mensajes .alert-success").wait_for()
        pa.goto("/feed")
        aviso = pa.locator("#aviso-moderacion")
        assert "No publiques avisos comerciales" in aviso.inner_text()
        aviso.get_by_role("button", name="Entendido").click()
        aviso.wait_for(state="detached")
        pa.reload()
        assert pa.locator("#aviso-moderacion").count() == 0

        # Historial
        p.click("#tab-historial")
        fila = p.locator("#filas-historial tr", has_text="Advertir").first
        fila.wait_for()
        assert "@dani_admin" in fila.inner_text() and "@ana_07" in fila.inner_text()
    finally:
        dani.close()
        ana.close()
        beto.close()
