"""CU-15 — Configurar los parámetros del sistema."""
import asyncio

import pytest

from app.features.m06_configuracion.cu15_configurar_parametros.handler import ConfigurarParametrosHandler
from app.features.m06_configuracion.cu15_configurar_parametros.request import ParametroRequest
from app.shared.config.provider import EnvConfigurationProvider
from app.shared.domain.entities import ClaveParametro
from app.shared.domain.errors import ErrorValidacion
from tests.fakes import FakeClock, FakeParameterRepository


def _handler(entorno):
    repo = FakeParameterRepository()
    return ConfigurarParametrosHandler(EnvConfigurationProvider(entorno), repo, FakeClock()), repo


@pytest.mark.parametrize("clave,valor,esperado", [
    (ClaveParametro.MAX_PUBLICACIONES_ACTIVAS, "10", 10),
    (ClaveParametro.ANTICIPACION_AVISO_CHAT_MIN, "60", 60),
    (ClaveParametro.DIAS_RETENCION_REPORTES, "1", 1),
    (ClaveParametro.HORAS_INACTIVIDAD_SESION, "72", 72),
    (ClaveParametro.DOMINIO_INSTITUCIONAL, " UNAS.edu.pe ", "unas.edu.pe"),
])
def test_acepta_valores_en_rango(clave, valor, esperado):
    h, _ = _handler({})
    assert asyncio.run(h.handle(ParametroRequest(clave=clave, valor=valor))).valor == esperado


@pytest.mark.parametrize("clave,valor", [
    (ClaveParametro.MAX_PUBLICACIONES_ACTIVAS, "0"), (ClaveParametro.MAX_PUBLICACIONES_ACTIVAS, "11"),
    (ClaveParametro.ANTICIPACION_AVISO_CHAT_MIN, "61"), (ClaveParametro.DIAS_RETENCION_REPORTES, "31"),
    (ClaveParametro.HORAS_INACTIVIDAD_SESION, "0"), (ClaveParametro.HORAS_INACTIVIDAD_SESION, "doce"),
    (ClaveParametro.DOMINIO_INSTITUCIONAL, "sin-punto"), (ClaveParametro.DOMINIO_INSTITUCIONAL, "a b.pe"),
])
def test_rechaza_fuera_de_rango_o_formato(clave, valor):
    h, _ = _handler({})
    with pytest.raises(ErrorValidacion):
        asyncio.run(h.handle(ParametroRequest(clave=clave, valor=valor)))


def test_revision_informa_rechazados_y_registra_efectivos():
    entorno = {"DOMINIO_INSTITUCIONAL": "unas.edu.pe", "CFG_MAX_PUBLICACIONES_ACTIVAS": "50",
               "CFG_DIAS_RETENCION_REPORTES": "10"}
    h, repo = _handler(entorno)
    revision = asyncio.run(h.revisar(entorno, registrar=True))
    assert len(revision.rechazados) == 1 and "CFG_MAX_PUBLICACIONES_ACTIVAS" in revision.rechazados[0]
    assert revision.efectivos["CFG_MAX_PUBLICACIONES_ACTIVAS"] == 3  # se conserva el valor válido
    assert revision.efectivos["CFG_DIAS_RETENCION_REPORTES"] == 10
    assert repo.guardados[ClaveParametro.DIAS_RETENCION_REPORTES].valor == 10


def test_sin_endpoint_publico():
    from app.main import app

    rutas = " ".join(app.openapi()["paths"])
    assert "parametro" not in rutas and "config" not in rutas  # RF-CFG-08


def test_cli(monkeypatch, capsys):
    from app.features.m06_configuracion.cu15_configurar_parametros import endpoint

    monkeypatch.setenv("DOMINIO_INSTITUCIONAL", "unas.edu.pe")
    monkeypatch.setenv("CFG_HORAS_INACTIVIDAD_SESION", "100")
    assert endpoint.main([]) == 1
    salida = capsys.readouterr()
    assert "CFG_HORAS_INACTIVIDAD_SESION = 12" in salida.out and "RECHAZADO" in salida.err
