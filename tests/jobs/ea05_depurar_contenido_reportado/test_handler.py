"""EA-05 — Eliminar contenido reportado vencido."""
import asyncio
from datetime import timedelta

from app.jobs.ea05_depurar_contenido_reportado.handler import DepurarContenidoReportadoHandler
from app.shared.domain.entities import CodigoMotivo, ContenidoReportado, Reporte, TipoObjetoReportado
from tests.fakes import FakeClock, FakeImageStorage, FakeReportRepository, imagen


def _reporte(reportes, imgs, reloj, dias):
    ahora = reloj.ahora()
    retenida = asyncio.run(imgs.copiar_a_retencion(asyncio.run(imgs.guardar(imagen(), "image/png"))))
    asyncio.run(reportes.crear(Reporte("", "u1", TipoObjetoReportado.CHAT, "c1", CodigoMotivo.SPAM, ahora,
                                       ahora + timedelta(days=dias), ContenidoReportado("u2", [], [retenida]))))
    return retenida


def test_purga_al_vencer_el_plazo_de_cada_reporte():
    reportes, imgs, reloj = FakeReportRepository(), FakeImageStorage(), FakeClock()
    corta = _reporte(reportes, imgs, reloj, 7)
    larga = _reporte(reportes, imgs, reloj, 30)  # el plazo queda fijado al reportar (RF-CFG-10)
    h = DepurarContenidoReportadoHandler(reportes, imgs, reloj)
    reloj.avanzar(days=6, hours=23)
    assert asyncio.run(h.handle())["reportes_eliminados"] == 0
    reloj.avanzar(hours=1)
    assert asyncio.run(h.handle()) == {"reportes_eliminados": 1, "imagenes_eliminadas": 1}
    assert corta not in imgs.objetos and larga in imgs.objetos and len(reportes.reportes) == 1


def test_cron_exige_secreto(monkeypatch):
    from fastapi.testclient import TestClient

    from app.jobs.ea05_depurar_contenido_reportado import endpoint
    from app.main import app

    h = DepurarContenidoReportadoHandler(FakeReportRepository(), FakeImageStorage(), FakeClock())
    app.dependency_overrides[endpoint.get_handler] = lambda: h
    try:
        monkeypatch.setenv("CRON_SECRET", "s3cr3t")
        cliente, ruta = TestClient(app), "/jobs/ea05-depurar-contenido-reportado"
        assert cliente.get(ruta, headers={"Authorization": "Bearer otro"}).status_code == 401
        assert cliente.get(ruta, headers={"Authorization": "Bearer s3cr3t"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
