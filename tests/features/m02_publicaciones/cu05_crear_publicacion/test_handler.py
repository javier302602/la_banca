"""CU-05 — Crear publicación."""
import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.features.m02_publicaciones.cu05_crear_publicacion.handler import CrearPublicacionHandler
from app.features.m02_publicaciones.cu05_crear_publicacion.request import CrearPublicacionRequest
from app.shared.domain.entities import TipoPublicacion
from app.shared.domain.errors import Conflicto
from tests.fakes import FakeClock, FakeConfig, FakePublicationRepository


def _req(**kw):
    datos = dict(tipo="NECESITO", titulo="  Busco calculadora  ", descripcion="Para el examen de las 10")
    datos.update(kw)
    return CrearPublicacionRequest(**datos)


def _handler(config=None):
    repo, reloj = FakePublicationRepository(), FakeClock()
    return CrearPublicacionHandler(repo, config or FakeConfig(), reloj), repo, reloj


def test_crea_con_duracion_fija_de_24_horas():
    h, repo, reloj = _handler()
    r = asyncio.run(h.handle("u1", "ana_07", _req()))
    assert r.titulo == "Busco calculadora"  # normalizado (RN-32)
    assert r.tipo is TipoPublicacion.NECESITO and r.nickname_autor == "ana_07"
    assert r.fecha_expiracion - r.fecha_creacion == timedelta(hours=24)
    assert r.segundos_restantes == 24 * 3600
    assert "correo" not in r.model_dump()


def test_ignora_duracion_enviada():
    req = _req(duracion=3, duracion_horas=1)  # RF-PUB-16: sin error
    h, *_ = _handler()
    assert asyncio.run(h.handle("u1", "ana_07", req)).segundos_restantes == 24 * 3600


def test_limite_de_activas_configurable():
    h, repo, reloj = _handler()
    for _ in range(3):
        asyncio.run(h.handle("u1", "ana_07", _req()))
    with pytest.raises(Conflicto, match="Ya tienes 3 publicaciones activas. Cierra una o espera a que expire"):
        asyncio.run(h.handle("u1", "ana_07", _req()))
    asyncio.run(h.handle("u2", "beto", _req()))  # otro autor no se ve afectado
    reloj.avanzar(hours=24)  # al vencer, liberan cupo
    asyncio.run(h.handle("u1", "ana_07", _req()))

    h2, *_ = _handler(FakeConfig(MAX_PUBLICACIONES_ACTIVAS=1))
    asyncio.run(h2.handle("u1", "ana_07", _req()))
    with pytest.raises(Conflicto, match="Ya tienes 1 publicaciones"):
        asyncio.run(h2.handle("u1", "ana_07", _req()))


def test_cupo():
    h, *_ = _handler()
    asyncio.run(h.handle("u1", "ana_07", _req()))
    cupo = asyncio.run(h.cupo("u1"))
    assert (cupo.activas, cupo.maximo) == (1, 3)


@pytest.mark.parametrize("campos,mensaje", [
    ({"tipo": None}, "tipo"), ({"tipo": "OTRO"}, "tipo"),
    ({"titulo": "   "}, "Debes ingresar el título"), ({"titulo": "x" * 81}, "entre 1 y 80"),
    ({"descripcion": ""}, "Debes ingresar la descripción"), ({"descripcion": "x" * 501}, "entre 1 y 500"),
])
def test_validaciones(campos, mensaje):
    with pytest.raises(ValidationError, match=mensaje):
        _req(**campos)


def test_limites_exactos_aceptados():
    _req(titulo="x" * 80, descripcion="y" * 500)
