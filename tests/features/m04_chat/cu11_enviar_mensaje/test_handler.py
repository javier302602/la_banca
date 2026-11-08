"""CU-11 — Enviar mensaje en un chat."""
import asyncio
from datetime import timedelta

import pytest

from app.features.m04_chat.cu11_enviar_mensaje.handler import EnviarMensajeHandler
from app.features.m04_chat.cu11_enviar_mensaje.request import MensajeEntrante
from app.shared.domain.entities import Chat, Mensaje
from app.shared.domain.errors import NoDisponible, NoEncontrado
from tests.fakes import FakeChatRepository, FakeClock, FakeImageStorage, imagen


def _escenario():
    chats, imgs, reloj = FakeChatRepository(), FakeImageStorage(), FakeClock()
    ahora = reloj.ahora()
    cid = asyncio.run(chats.crear_con_primer_mensaje(
        Chat("", "p1", "autor", "lector", ahora, ahora, ahora + timedelta(hours=24)),
        Mensaje("", "", "lector", "beto", ahora, texto="hola")))
    return EnviarMensajeHandler(chats, imgs, reloj), chats, imgs, reloj, cid


def _enviar(h, cid, usuario="autor", **kw):
    return asyncio.run(h.handle(usuario, f"nick_{usuario}", cid, MensajeEntrante(**(kw or {"texto": "respuesta"}))))


def test_mensaje_reinicia_expiracion():
    h, chats, _, reloj, cid = _escenario()
    reloj.avanzar(hours=23)
    r = _enviar(h, cid)
    assert r.es_propio and r.texto == "respuesta" and r.imagen_url is None
    assert chats.chats[cid].fecha_expiracion == reloj.ahora() + timedelta(hours=24)  # RF-CHT-12
    reloj.avanzar(hours=23)
    _enviar(h, cid, usuario="lector")  # sigue vigente gracias al reinicio


def test_imagen_con_url_protegida():
    h, chats, imgs, _, cid = _escenario()
    r = _enviar(h, cid, imagen=imagen("WEBP"))
    assert r.imagen_url == f"/api/chats/{cid}/mensajes/{r.id}/imagen"
    assert chats.mensajes[r.id].imagen.referencia in imgs.objetos


def test_chat_expirado_no_admite_mensajes():
    h, _, imgs, reloj, cid = _escenario()
    reloj.avanzar(hours=24)
    with pytest.raises(NoDisponible, match="Este chat expiró"):
        _enviar(h, cid, imagen=imagen())
    assert not imgs.objetos


def test_tercero_no_puede_enviar():
    h, *_, cid = _escenario()
    with pytest.raises(NoEncontrado):
        _enviar(h, cid, usuario="intruso")  # RNF-SEG-04


def test_expira_entre_lectura_y_escritura():
    h, chats, imgs, reloj, cid = _escenario()

    async def expirado(*_):
        return None

    chats.agregar_mensaje = expirado
    with pytest.raises(NoDisponible):
        _enviar(h, cid, imagen=imagen())
    assert not imgs.objetos
