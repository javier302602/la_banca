"""CU-09 — Ver detalle de una publicación."""
import asyncio
from datetime import timedelta

import pytest

from app.features.m03_feed.cu09_ver_detalle_publicacion.handler import VerDetallePublicacionHandler
from app.shared.domain.entities import Chat, Mensaje, Publicacion, TipoPublicacion
from app.shared.domain.errors import NoDisponible
from tests.fakes import FakeChatRepository, FakeClock, FakePublicationRepository


def _escenario():
    pubs, chats, reloj = FakePublicationRepository(), FakeChatRepository(), FakeClock()
    ahora = reloj.ahora()
    pid = asyncio.run(pubs.crear(Publicacion("", "autor", "ana", TipoPublicacion.NECESITO, "t", "descripción",
                                             ahora, ahora + timedelta(hours=24))))
    return VerDetallePublicacionHandler(pubs, chats, reloj), pubs, chats, reloj, pid


def test_detalle_de_publicacion_ajena():
    h, *_, pid = _escenario()
    d = asyncio.run(h.handle("lector", pid))
    assert d.descripcion == "descripción" and d.nickname_autor == "ana"
    assert d.puede_responder and d.puede_reportar and not d.es_propia


def test_propia_sin_responder_ni_reportar():
    h, *_, pid = _escenario()
    d = asyncio.run(h.handle("autor", pid))
    assert d.es_propia and not d.puede_responder and not d.puede_reportar  # RF-FED-12


def test_ofrece_chat_existente():
    h, _, chats, reloj, pid = _escenario()
    ahora = reloj.ahora()
    cid = asyncio.run(chats.crear_con_primer_mensaje(
        Chat("", pid, "autor", "lector", ahora, ahora, ahora + timedelta(hours=24)),
        Mensaje("", "", "lector", "beto", ahora, texto="hola")))
    d = asyncio.run(h.handle("lector", pid))
    assert d.chat_existente_id == cid and not d.puede_responder  # RF-CHT-23


def test_no_disponible_si_vencio_o_no_existe():
    h, _, _, reloj, pid = _escenario()
    with pytest.raises(NoDisponible, match="Esta publicación ya no está disponible"):
        asyncio.run(h.handle("lector", "no-existe"))
    reloj.avanzar(hours=24)
    with pytest.raises(NoDisponible):
        asyncio.run(h.handle("lector", pid))
