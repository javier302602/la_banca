"""Fase 2 — Publicaciones de 24 h: ocultar sin borrar, video, reacciones y datos de la tarjeta del feed."""
import asyncio

import pytest

from app.features.m02_publicaciones.cu05_crear_publicacion.handler import CrearPublicacionHandler
from app.features.m02_publicaciones.cu05_crear_publicacion.request import CrearPublicacionRequest
from app.features.m02_publicaciones.cu21_reaccionar_publicacion.handler import ReaccionarPublicacionHandler
from app.features.m02_publicaciones.cu21_reaccionar_publicacion.request import ReaccionarRequest
from app.features.m03_feed.cu08_consultar_feed.handler import ConsultarFeedHandler, extracto
from app.features.m03_feed.cu08_consultar_feed.request import ConsultarFeedRequest
from app.features.m03_feed.cu09_ver_detalle_publicacion.handler import VerDetallePublicacionHandler
from app.jobs.ea03_limpiar_chats_expirados.handler import LimpiarChatsExpiradosHandler
from app.shared.domain.entities import TipoReaccion
from app.shared.domain.errors import ErrorValidacion, NoDisponible
from app.shared.domain.reglas import detectar_formato_video
from tests.fakes import (FakeChatRepository, FakeClock, FakeConfig, FakeImageStorage, FakePublicationRepository,
                         FakeReactionRepository)

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
WEBM = bytes.fromhex("1a45dfa3") + b"\x00" * 64
MOV = b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 64


def correr(c):
    return asyncio.run(c)


def req(descripcion="La presto"):
    return CrearPublicacionRequest(tipo="OFREZCO", titulo="Calculadora", descripcion=descripcion)


@pytest.fixture
def mundo():
    pubs, imgs, reloj, reacciones = FakePublicationRepository(), FakeImageStorage(), FakeClock(), FakeReactionRepository()
    return {"pubs": pubs, "imgs": imgs, "reloj": reloj, "reacciones": reacciones,
            "crear": CrearPublicacionHandler(pubs, FakeConfig(), reloj, imgs, tamano_max_video=1024),
            "feed": ConsultarFeedHandler(pubs, reloj, reacciones=reacciones),
            "detalle": VerDetallePublicacionHandler(pubs, FakeChatRepository(), reloj, imagenes=imgs,
                                                    reacciones=reacciones),
            "reaccionar": ReaccionarPublicacionHandler(pubs, reacciones, reloj)}


# --- 24 h: ocultar sin borrar ---------------------------------------------------------------
def test_vencida_se_oculta_pero_no_se_borra(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req()))
    assert r.segundos_restantes == 24 * 3600
    mundo["reloj"].avanzar(hours=24)
    assert correr(mundo["feed"].handle("u2", ConsultarFeedRequest())).items == []
    with pytest.raises(NoDisponible):
        correr(mundo["detalle"].handle("u2", r.id))
    assert r.id in mundo["pubs"].publicaciones  # sigue guardada para revisión de los admins


def test_video_se_conserva_hasta_29_dias_despues_de_vencer(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req(), [], MP4))
    clave = mundo["pubs"].publicaciones[r.id].video.referencia
    ea03 = LimpiarChatsExpiradosHandler(FakeChatRepository(), mundo["imgs"], mundo["reloj"], mundo["pubs"])
    mundo["reloj"].avanzar(days=29)  # venció hace 28 días
    assert correr(ea03.handle())["imagenes_de_publicaciones_eliminadas"] == 0
    mundo["reloj"].avanzar(days=1)
    assert correr(ea03.handle())["imagenes_de_publicaciones_eliminadas"] == 1
    assert clave not in mundo["imgs"].objetos


# --- Video ------------------------------------------------------------------------------------
def test_detecta_video_por_contenido():
    assert detectar_formato_video(MP4) == "video/mp4"
    assert detectar_formato_video(WEBM) == "video/webm"
    assert detectar_formato_video(MOV) is None
    assert detectar_formato_video(b"no es video") is None


def test_crea_con_video_y_lo_sirve(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req(), [], WEBM))
    assert r.video == f"/api/publicaciones/{r.id}/video"
    descargado = correr(mundo["detalle"].video(r.id))
    assert descargado.contenido == WEBM and descargado.mime_type == "video/webm"


@pytest.mark.parametrize("video, mensaje", [(MOV, "Formato de video no permitido"),
                                            (MP4 + b"\x00" * 1024, "supera el tamaño máximo")])
def test_rechaza_video_invalido_sin_dejar_archivos(mundo, video, mensaje):
    with pytest.raises(ErrorValidacion, match=mensaje):
        correr(mundo["crear"].handle("u1", "ana", req(), [], video))
    assert not mundo["imgs"].objetos and not mundo["pubs"].publicaciones


# --- Reacciones -------------------------------------------------------------------------------
def test_reaccion_unica_por_estudiante_cambia_y_se_quita(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req()))
    reaccionar = mundo["reaccionar"]
    correr(reaccionar.handle("u2", r.id, ReaccionarRequest(tipo=TipoReaccion.ME_GUSTA)))
    res = correr(reaccionar.handle("u3", r.id, ReaccionarRequest(tipo=TipoReaccion.ME_GUSTA)))
    assert res.conteos == {TipoReaccion.ME_GUSTA: 2} and res.total == 2 and res.mia is TipoReaccion.ME_GUSTA
    res = correr(reaccionar.handle("u3", r.id, ReaccionarRequest(tipo=TipoReaccion.ME_ENCANTA)))
    assert res.conteos == {TipoReaccion.ME_GUSTA: 1, TipoReaccion.ME_ENCANTA: 1}
    res = correr(reaccionar.handle("u3", r.id, ReaccionarRequest(tipo=None)))
    assert res.conteos == {TipoReaccion.ME_GUSTA: 1} and res.mia is None


def test_no_se_reacciona_a_una_vencida(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req()))
    mundo["reloj"].avanzar(hours=24)
    with pytest.raises(NoDisponible):
        correr(mundo["reaccionar"].handle("u2", r.id, ReaccionarRequest(tipo=TipoReaccion.ME_GUSTA)))


def test_feed_y_detalle_muestran_reacciones_extracto_y_video(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req("x " * 200), [], MP4))
    correr(mundo["reaccionar"].handle("u2", r.id, ReaccionarRequest(tipo=TipoReaccion.ME_DIVIERTE)))
    item = correr(mundo["feed"].handle("u2", ConsultarFeedRequest())).items[0]
    assert item.reacciones.mia is TipoReaccion.ME_DIVIERTE and item.reacciones.total == 1
    assert item.video and len(item.extracto) == 140 and item.extracto.endswith("…")
    detalle = correr(mundo["detalle"].handle("u1", r.id))
    assert detalle.reacciones.total == 1 and detalle.reacciones.mia is None and detalle.video


def test_extracto_corto_no_se_corta():
    assert extracto("  Hola\n mundo  ") == "Hola mundo"
