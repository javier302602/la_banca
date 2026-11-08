"""CU-12 — Ver mis chats activos y abrir uno (+ EA-04)."""
import asyncio
from datetime import timedelta

import pytest

from app.features.m04_chat.cu12_ver_mis_chats.handler import VerMisChatsHandler
from app.features.m04_chat.cu12_ver_mis_chats.request import AbrirChatRequest
from app.shared.domain.entities import Chat, ImagenAdjunta, Mensaje, TipoPublicacion
from app.shared.domain.errors import NoDisponible, NoEncontrado
from tests.fakes import FakeChatRepository, FakeClock, FakeConfig, FakeImageStorage, imagen


def _chat(chats, reloj, respondedor="lector", titulo="t", texto="hola"):
    ahora = reloj.ahora()
    return asyncio.run(chats.crear_con_primer_mensaje(
        Chat("", f"p_{titulo}", "autor", respondedor, ahora, ahora, ahora + timedelta(hours=24),
             TipoPublicacion.NECESITO, titulo, nickname_autor="ana", nickname_respondedor=f"nick_{respondedor}",
             ultima_lectura={respondedor: ahora}),
        Mensaje("", "", respondedor, f"nick_{respondedor}", ahora, texto=texto)))


def _handler(config=None):
    chats, imgs, reloj = FakeChatRepository(), FakeImageStorage(), FakeClock()
    return VerMisChatsHandler(chats, imgs, config or FakeConfig(), reloj), chats, imgs, reloj


def test_lista_por_ultimo_mensaje_con_no_leidos():
    h, chats, _, reloj = _handler()
    viejo = _chat(chats, reloj, titulo="viejo")
    reloj.avanzar(minutes=5)
    nuevo = _chat(chats, reloj, respondedor="otro", titulo="nuevo")
    lista = asyncio.run(h.handle("autor"))
    assert [c.id for c in lista.items] == [nuevo, viejo]  # RF-CHT-18
    assert lista.items[0].nickname_contraparte == "nick_otro" and lista.items[0].no_leidos
    # RF-CHT-18 / RN-34: 14:05 UTC → 09:05 en America/Lima, calculado en el servidor
    assert [c.hora_ultimo_mensaje for c in lista.items] == ["09:05", "09:00"]
    asyncio.run(h.abrir("autor", nuevo))
    assert not asyncio.run(h.handle("autor")).items[0].no_leidos  # RF-CHT-21
    assert [c.id for c in asyncio.run(h.handle("lector")).items] == [viejo]


def test_abrir_no_reinicia_expiracion_y_marca_propios():
    h, chats, _, reloj = _handler()
    cid = _chat(chats, reloj)
    reloj.avanzar(hours=1)
    d = asyncio.run(h.abrir("autor", cid))
    assert d.segundos_restantes == 23 * 3600  # RF-CHT-12: leer no reinicia
    assert d.nickname_contraparte == "nick_lector" and d.titulo_publicacion == "t"
    assert [m.es_propio for m in d.mensajes] == [False]
    assert [m.hora for m in d.mensajes] == ["09:00"]  # RF-CHT-11: 14:00 UTC → 09:00 en Lima
    assert "correo" not in d.model_dump_json()


def test_aviso_ea04_con_anticipacion_configurable():
    h, chats, _, reloj = _handler()
    cid = _chat(chats, reloj)
    reloj.avanzar(hours=23, minutes=49)
    assert not asyncio.run(h.abrir("autor", cid)).aviso.activo  # faltan 11 min
    reloj.avanzar(minutes=1)
    aviso = asyncio.run(h.abrir("autor", cid)).aviso
    assert aviso.activo and aviso.mensaje == (
        "Este chat expira en 10 min por inactividad. Envía un mensaje para mantenerlo")
    reloj.avanzar(minutes=1, seconds=30)
    assert asyncio.run(h.abrir("autor", cid)).aviso.minutos == 9  # 8 min 30 s → 9

    h2, chats2, _, reloj2 = _handler(FakeConfig(ANTICIPACION_AVISO_CHAT_MIN=30))
    cid2 = _chat(chats2, reloj2)
    reloj2.avanzar(hours=23, minutes=31)
    assert asyncio.run(h2.abrir("autor", cid2)).aviso.activo


def test_chat_expirado_o_ajeno():
    h, chats, _, reloj = _handler()
    cid = _chat(chats, reloj)
    with pytest.raises(NoEncontrado):
        asyncio.run(h.abrir("intruso", cid))  # RNF-SEG-04
    reloj.avanzar(hours=24)
    with pytest.raises(NoDisponible, match="Este chat expiró"):
        asyncio.run(h.abrir("autor", cid))
    assert asyncio.run(h.handle("autor")).items == []


def test_sondeo_incremental():
    h, chats, _, reloj = _handler()
    cid = _chat(chats, reloj)
    primero = asyncio.run(h.abrir("autor", cid)).mensajes[-1].fecha_envio
    reloj.avanzar(seconds=1)
    asyncio.run(chats.agregar_mensaje(Mensaje("", cid, "lector", "nick_lector", reloj.ahora(), texto="nuevo"),
                                      reloj.ahora() + timedelta(hours=24)))
    nuevos = asyncio.run(h.abrir("autor", cid, AbrirChatRequest(despues_de=primero))).mensajes
    assert [m.texto for m in nuevos] == ["nuevo"]


def test_imagen_solo_para_participantes():
    h, chats, imgs, reloj = _handler()
    cid = _chat(chats, reloj)
    referencia = asyncio.run(imgs.guardar(imagen(), "image/png"))
    mid = asyncio.run(chats.agregar_mensaje(
        Mensaje("", cid, "lector", "nick_lector", reloj.ahora(), imagen=ImagenAdjunta(referencia, "image/png", 10)),
        reloj.ahora() + timedelta(hours=24)))
    descarga = asyncio.run(h.imagen("autor", cid, mid))
    assert descarga.mime_type == "image/png" and descarga.contenido.startswith(b"\x89PNG")
    with pytest.raises(NoEncontrado):
        asyncio.run(h.imagen("intruso", cid, mid))
    with pytest.raises(NoEncontrado):
        asyncio.run(h.imagen("autor", cid, "no-existe"))
