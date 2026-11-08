"""CU-10 — Responder a una publicación."""
import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.features.m04_chat.cu10_responder_publicacion.handler import ResponderPublicacionHandler
from app.features.m04_chat.cu10_responder_publicacion.request import MensajeEntrante
from app.shared.domain.entities import EstadoPublicacion, Publicacion, TipoPublicacion
from app.shared.domain.errors import Conflicto, ErrorValidacion, NoDisponible, Prohibido
from tests.fakes import FakeChatRepository, FakeClock, FakeImageStorage, FakePublicationRepository, imagen


def _escenario():
    pubs, chats, imgs, reloj = FakePublicationRepository(), FakeChatRepository(), FakeImageStorage(), FakeClock()
    ahora = reloj.ahora()
    pid = asyncio.run(pubs.crear(Publicacion("", "autor", "ana", TipoPublicacion.OFREZCO, "Apuntes", "d", ahora,
                                             ahora + timedelta(hours=24))))
    return ResponderPublicacionHandler(pubs, chats, imgs, reloj), pubs, chats, imgs, reloj, pid


def _responder(h, pid, usuario="lector", **kw):
    return asyncio.run(h.handle(usuario, f"nick_{usuario}", pid, MensajeEntrante(**(kw or {"texto": "Hola"}))))


def test_crea_chat_y_primer_mensaje():
    h, _, chats, _, reloj, pid = _escenario()
    r = _responder(h, pid)
    chat = chats.chats[r.chat_id]
    assert r.nickname_autor == "ana" and chat.participantes == ("autor", "lector")
    assert chat.fecha_expiracion == reloj.ahora() + timedelta(hours=24)  # RF-CHT-03
    assert (chat.titulo_publicacion, chat.tipo_publicacion) == ("Apuntes", TipoPublicacion.OFREZCO)
    [mensaje] = chats.mensajes.values()
    assert mensaje.chat_id == r.chat_id and mensaje.texto == "Hola"


def test_primer_mensaje_con_imagen_sin_exif():
    h, _, chats, imgs, _, pid = _escenario()
    _responder(h, pid, imagen=imagen("JPEG"))
    [mensaje] = chats.mensajes.values()
    assert mensaje.texto is None and mensaje.imagen.mime_type == "image/jpeg"
    assert mensaje.imagen.referencia in imgs.objetos


def test_no_responder_propia_ni_no_activa():
    h, pubs, _, _, reloj, pid = _escenario()
    with pytest.raises(Prohibido):
        _responder(h, pid, usuario="autor")  # RF-CHT-04
    pubs.publicaciones[pid].estado = EstadoPublicacion.CLOSED
    with pytest.raises(NoDisponible, match="Esta publicación ya no está disponible"):
        _responder(h, pid)  # RF-CHT-06


def test_un_chat_activo_por_usuario_y_publicacion():
    h, *_, pid = _escenario()
    primero = _responder(h, pid)
    with pytest.raises(Conflicto) as error:
        _responder(h, pid)
    assert error.value.extra["chat_id"] == primero.chat_id  # RF-CHT-23
    _responder(h, pid, usuario="otro")  # RF-CHT-07


def test_responder_de_nuevo_tras_expirar_crea_chat_nuevo():
    h, pubs, chats, imgs, reloj, pid = _escenario()
    reloj.avanzar(hours=1)  # el chat se crea 1 h después que la publicación
    viejo = _responder(h, pid, imagen=imagen())
    pubs.publicaciones[pid].fecha_expiracion += timedelta(hours=2)  # publicación aún vigente al expirar el chat
    reloj.avanzar(hours=24)
    nuevo = _responder(h, pid)
    assert nuevo.chat_id != viejo.chat_id and viejo.chat_id not in chats.chats  # RF-CHT-24
    assert len(chats.mensajes) == 1 and not imgs.objetos  # sin mensajes ni imágenes del anterior


@pytest.mark.parametrize("datos,mensaje", [
    ({}, "Escribe un mensaje o adjunta una imagen"),
    ({"texto": "   "}, "Escribe un mensaje"),
    ({"texto": "x" * 501}, "entre 1 y 500"),
    ({"texto": "hola", "imagen": b"\x89PNG\r\n\x1a\n"}, "no ambos"),
    ({"imagen": b"GIF89a"}, "Formato de imagen no permitido"),
])
def test_validacion_del_mensaje(datos, mensaje):
    with pytest.raises(ValidationError, match=mensaje):
        MensajeEntrante(**datos)


def test_imagen_corrupta_no_deja_chat():
    h, _, chats, imgs, _, pid = _escenario()
    with pytest.raises(ErrorValidacion):
        _responder(h, pid, imagen=imagen()[:30])
    assert not chats.chats and not imgs.objetos


def test_fallo_al_crear_borra_la_imagen():
    h, _, chats, imgs, _, pid = _escenario()

    async def falla(*_):
        raise RuntimeError("mongo caído")

    chats.crear_con_primer_mensaje = falla
    with pytest.raises(RuntimeError):
        _responder(h, pid, imagen=imagen())
    assert not imgs.objetos  # RNF-FIA-03
