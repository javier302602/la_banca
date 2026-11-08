"""CU-13 — Reportar una publicación."""
import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.features.m05_reportes.cu13_reportar_publicacion.handler import ReportarPublicacionHandler
from app.features.m05_reportes.cu13_reportar_publicacion.request import ReporteRequest
from app.shared.domain.entities import CodigoMotivo, EstadoPublicacion, Publicacion, TipoObjetoReportado, TipoPublicacion
from app.shared.domain.errors import Conflicto, NoDisponible, Prohibido
from tests.fakes import FakeClock, FakeConfig, FakePublicationRepository, FakeReportRepository


def _escenario(config=None):
    pubs, reportes, reloj = FakePublicationRepository(), FakeReportRepository(), FakeClock()
    ahora = reloj.ahora()
    pid = asyncio.run(pubs.crear(Publicacion("", "autor", "ana", TipoPublicacion.OFREZCO, "Vendo", "Barato", ahora,
                                             ahora + timedelta(hours=24))))
    return ReportarPublicacionHandler(pubs, reportes, config or FakeConfig(), reloj), pubs, reportes, reloj, pid


def _reportar(h, pid, usuario="lector", **kw):
    datos = {"codigo_motivo": "SPAM", **kw}
    return asyncio.run(h.handle(usuario, pid, ReporteRequest(**datos)))


def test_registra_reporte_con_copia_y_plazo():
    h, pubs, reportes, reloj, pid = _escenario()
    assert _reportar(h, pid, observacion="  repetido  ").mensaje == "Reporte registrado. Gracias por avisar"
    [r] = reportes.reportes.values()
    assert (r.reportante_id, r.objeto_id, r.tipo_objeto) == ("lector", pid, TipoObjetoReportado.PUBLICATION)
    assert r.codigo_motivo is CodigoMotivo.SPAM and r.observacion == "repetido"
    assert r.fecha_reporte == reloj.ahora() and r.fecha_retencion_fin == reloj.ahora() + timedelta(days=7)
    assert r.contenido.usuario_reportado_id == "autor"  # RF-REP-07
    assert r.contenido.datos_publicacion["description"] == "Barato"  # RF-REP-06 (publicationData)
    assert r.contenido.datos_publicacion["title"] == "Vendo" and r.contenido.datos_publicacion["type"] == "OFREZCO"
    assert r.contenido.capturado_en == reloj.ahora() and r.contenido.mensajes == []
    assert pubs.publicaciones[pid].estado is EstadoPublicacion.ACTIVE  # RF-REP-10


def test_plazo_configurable():
    h, _, reportes, reloj, pid = _escenario(FakeConfig(DIAS_RETENCION_REPORTES=30))
    _reportar(h, pid)
    assert next(iter(reportes.reportes.values())).fecha_retencion_fin == reloj.ahora() + timedelta(days=30)


def test_duplicado_y_propia():
    h, *_, pid = _escenario()
    _reportar(h, pid)
    with pytest.raises(Conflicto, match="Ya reportaste esta publicación"):
        _reportar(h, pid, codigo_motivo="FRAUD")  # RF-REP-12
    with pytest.raises(Prohibido):
        _reportar(h, pid, usuario="autor")  # RF-REP-13
    _reportar(h, pid, usuario="otro")


def test_publicacion_no_activa():
    h, _, _, reloj, pid = _escenario()
    reloj.avanzar(hours=24)
    with pytest.raises(NoDisponible):
        _reportar(h, pid)


def test_validaciones():
    with pytest.raises(ValidationError, match="Selecciona un motivo"):
        ReporteRequest()
    with pytest.raises(ValidationError):
        ReporteRequest(codigo_motivo="INVENTADO")
    with pytest.raises(ValidationError, match="hasta 300"):
        ReporteRequest(codigo_motivo="OTHER", observacion="x" * 301)
    assert ReporteRequest(codigo_motivo="OTHER", observacion="x" * 300).observacion == "x" * 300
    assert ReporteRequest(codigo_motivo="OTHER", observacion="   ").observacion is None
