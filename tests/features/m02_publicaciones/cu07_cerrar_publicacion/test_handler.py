"""CU-07 — Cerrar publicación manualmente."""
import asyncio
from datetime import timedelta

import pytest

from app.features.m02_publicaciones.cu07_cerrar_publicacion.handler import CerrarPublicacionHandler
from app.shared.domain.entities import EstadoPublicacion, Publicacion, TipoPublicacion
from app.shared.domain.errors import NoDisponible, NoEncontrado, Prohibido
from tests.fakes import FakeClock, FakePublicationRepository


def _escenario():
    repo, reloj = FakePublicationRepository(), FakeClock()
    ahora = reloj.ahora()
    pid = asyncio.run(repo.crear(Publicacion("", "u1", "ana", TipoPublicacion.ACTIVIDAD, "t", "d", ahora,
                                             ahora + timedelta(hours=24))))
    return CerrarPublicacionHandler(repo, reloj), repo, reloj, pid


def test_autor_cierra_y_no_puede_reactivar():
    h, repo, _, pid = _escenario()
    asyncio.run(h.handle("u1", pid))
    assert repo.publicaciones[pid].estado is EstadoPublicacion.CLOSED
    with pytest.raises(NoDisponible, match="Esta publicación ya no está disponible"):
        asyncio.run(h.handle("u1", pid))


def test_solo_el_autor():
    h, _, _, pid = _escenario()
    with pytest.raises(Prohibido):
        asyncio.run(h.handle("u2", pid))


def test_publicacion_vencida_o_inexistente():
    h, _, reloj, pid = _escenario()
    with pytest.raises(NoEncontrado):
        asyncio.run(h.handle("u1", "no-existe"))
    reloj.avanzar(hours=24)
    with pytest.raises(NoDisponible):
        asyncio.run(h.handle("u1", pid))
