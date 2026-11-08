"""CU-08 — Consultar el feed «Ahora» (+ EA-02 al consultar)."""
import asyncio
from datetime import timedelta

import pytest
from bson import ObjectId

from app.features.m03_feed.cu08_consultar_feed.handler import MSG_VACIO, MSG_VACIO_TIPO, ConsultarFeedHandler
from app.features.m03_feed.cu08_consultar_feed.repository import codificar_cursor, decodificar_cursor
from app.features.m03_feed.cu08_consultar_feed.request import ConsultarFeedRequest
from app.shared.domain.entities import EstadoPublicacion, Publicacion, TipoPublicacion
from app.shared.domain.errors import ErrorValidacion
from tests.fakes import FakeClock, FakePublicationRepository


def publicar(repo, reloj, autor="u2", tipo=TipoPublicacion.NECESITO, titulo="t"):
    ahora = reloj.ahora()
    return asyncio.run(repo.crear(Publicacion("", autor, f"nick_{autor}", tipo, titulo, "d", ahora,
                                              ahora + timedelta(hours=24))))


def consultar(repo, reloj, **kw):
    return asyncio.run(ConsultarFeedHandler(repo, reloj).handle("u1", ConsultarFeedRequest(**kw)))


def test_solo_vigentes_al_consultar_mas_recientes_primero():
    repo, reloj = FakePublicationRepository(), FakeClock()
    vieja = publicar(repo, reloj, titulo="vieja")
    reloj.avanzar(hours=1)
    cerrada = publicar(repo, reloj, titulo="cerrada")
    repo.publicaciones[cerrada].estado = EstadoPublicacion.CLOSED
    publicar(repo, reloj, titulo="nueva", autor="u1")
    feed = consultar(repo, reloj)
    assert [i.titulo for i in feed.items] == ["nueva", "vieja"]
    assert feed.items[0].es_propia and not feed.items[1].es_propia  # «Tu publicación» (RF-FED-07)
    reloj.avanzar(hours=23)  # «vieja» cumple 24 h: EA-02 sin cron
    assert [i.titulo for i in consultar(repo, reloj).items] == ["nueva"]
    assert vieja in repo.publicaciones  # no se borra, solo se excluye


def test_mismo_instante_ordena_por_orden_de_registro():
    repo, reloj = FakePublicationRepository(), FakeClock()
    for titulo in ("a", "b", "c"):
        publicar(repo, reloj, titulo=titulo)
    assert [i.titulo for i in consultar(repo, reloj).items] == ["c", "b", "a"]  # RF-FED-03


def test_filtro_por_tipo_y_mensajes_de_vacio():
    repo, reloj = FakePublicationRepository(), FakeClock()
    assert consultar(repo, reloj).mensaje_vacio == MSG_VACIO
    publicar(repo, reloj, tipo=TipoPublicacion.OFREZCO)
    publicar(repo, reloj, tipo=TipoPublicacion.NECESITO)
    solo = consultar(repo, reloj, tipo="OFREZCO")
    assert [i.tipo for i in solo.items] == [TipoPublicacion.OFREZCO] and solo.mensaje_vacio is None
    assert consultar(repo, reloj, tipo="ACTIVIDAD").mensaje_vacio == MSG_VACIO_TIPO


def test_paginado_por_bloques_de_20():
    repo, reloj = FakePublicationRepository(), FakeClock()
    for i in range(45):
        publicar(repo, reloj, titulo=str(i))
        reloj.avanzar(seconds=1)
    vistos, cursor = [], None
    for esperado in (20, 20, 5):
        feed = consultar(repo, reloj, cursor=cursor)
        assert len(feed.items) == esperado and feed.tamano_bloque == 20
        vistos += [i.titulo for i in feed.items]
        cursor = feed.siguiente_cursor
    assert cursor is None and vistos == [str(i) for i in range(44, -1, -1)]  # RF-FED-19


def test_no_expone_correo_y_tiempo_restante():
    repo, reloj = FakePublicationRepository(), FakeClock()
    publicar(repo, reloj)
    reloj.avanzar(hours=2)
    item = consultar(repo, reloj).items[0]
    assert item.segundos_restantes == 22 * 3600
    assert "correo" not in item.model_dump() and item.nickname_autor == "nick_u2"


def test_cursor_mongo_ida_y_vuelta_e_invalido():
    reloj = FakeClock()
    id_ = ObjectId()
    assert decodificar_cursor(codificar_cursor(reloj.ahora(), id_)) == (reloj.ahora(), id_)
    for malo in ("xxx", "e30", codificar_cursor(reloj.ahora(), id_)[:-3]):
        with pytest.raises(ErrorValidacion):
            decodificar_cursor(malo)
