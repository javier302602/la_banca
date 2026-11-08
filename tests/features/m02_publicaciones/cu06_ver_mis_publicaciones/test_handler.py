"""CU-06 — Ver mis publicaciones activas."""
import asyncio
from datetime import timedelta

from app.features.m02_publicaciones.cu06_ver_mis_publicaciones.handler import VerMisPublicacionesHandler
from app.shared.domain.entities import Publicacion, TipoPublicacion
from tests.fakes import FakeClock, FakePublicationRepository


def publicar(repo, reloj, autor="u1", titulo="t"):
    ahora = reloj.ahora()
    return asyncio.run(repo.crear(Publicacion("", autor, "nick", TipoPublicacion.OFREZCO, titulo, "d", ahora,
                                              ahora + timedelta(hours=24))))


def test_lista_solo_propias_vigentes_mas_recientes_primero():
    repo, reloj = FakePublicationRepository(), FakeClock()
    publicar(repo, reloj, titulo="vieja")
    reloj.avanzar(hours=1)
    publicar(repo, reloj, titulo="nueva")
    publicar(repo, reloj, autor="u2", titulo="ajena")
    reloj.avanzar(hours=23, minutes=30)  # «vieja» vence a las 24 h desde su creación
    r = asyncio.run(VerMisPublicacionesHandler(repo, reloj).handle("u1"))
    assert [p.titulo for p in r.items] == ["nueva"]
    assert r.items[0].segundos_restantes == 30 * 60
    assert r.ahora == reloj.ahora()


def test_orden_descendente():
    repo, reloj = FakePublicationRepository(), FakeClock()
    for titulo in ("a", "b", "c"):
        publicar(repo, reloj, titulo=titulo)
        reloj.avanzar(minutes=1)
    r = asyncio.run(VerMisPublicacionesHandler(repo, reloj).handle("u1"))
    assert [p.titulo for p in r.items] == ["c", "b", "a"]
