"""Fase 3 — Audios en el chat, respuestas con Range y ubicación en vivo (CU-22)."""
import asyncio
from datetime import timedelta

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.features.m04_chat.cu11_enviar_mensaje.handler import EnviarMensajeHandler
from app.features.m04_chat.cu11_enviar_mensaje.request import MensajeEntrante
from app.features.m04_chat.cu22_compartir_ubicacion.handler import CompartirUbicacionHandler
from app.features.m04_chat.cu22_compartir_ubicacion.request import PosicionEntrante
from app.shared.domain.audios import detectar_tipo_audio, validar_audio
from app.shared.domain.entities import Chat, Mensaje
from app.shared.domain.errors import ErrorValidacion
from app.shared.web.medios import respuesta_con_rango
from tests.fakes import FakeChatRepository, FakeClock, FakeImageStorage, FakeUbicacionRepository

AUDIOS = {
    "mp3": b"ID3\x04\x00" + b"\x00" * 40,
    "wav": b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 40,
    "ogg": b"OggS\x00\x02" + b"\x00" * 40,
    "flac": b"fLaC\x00\x00\x00\x22" + b"\x00" * 40,
    "m4a": b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 40,
    "aac": b"\xff\xf1\x50\x80" + b"\x00" * 40,
}
MP3_SIN_ID3 = b"\xff\xfb\x90\x64" + b"\x00" * 40


def correr(c):
    return asyncio.run(c)


def _chat():
    chats, imgs, reloj = FakeChatRepository(), FakeImageStorage(), FakeClock()
    ahora = reloj.ahora()
    cid = correr(chats.crear_con_primer_mensaje(
        Chat("", "p1", "autor", "lector", ahora, ahora, ahora + timedelta(hours=24)),
        Mensaje("", "", "lector", "beto", ahora, texto="hola")))
    return chats, imgs, reloj, cid


# --- Audios -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("tipo", list(AUDIOS))
def test_detecta_cada_formato_de_audio_por_contenido(tipo):
    assert detectar_tipo_audio(AUDIOS[tipo]) == tipo


def test_mp3_sin_id3_y_rechazos():
    assert detectar_tipo_audio(MP3_SIN_ID3) == "mp3"
    for no_audio in (b"%PDF-1.7", b"MZ\x90\x00", b"\x00\x00\x00\x18ftypqt  ", b"hola mundo", b""):
        assert detectar_tipo_audio(no_audio) is None


def test_validar_audio_tamano_y_nombre():
    v = validar_audio(AUDIOS["flac"], "../Mi canción.mp3", tamano_max=1024)
    assert (v.tipo, v.mime_type, v.nombre) == ("flac", "audio/flac", "Mi canción.flac")  # extensión real
    with pytest.raises(ValueError, match="tamaño máximo de 1 MB"):
        validar_audio(AUDIOS["mp3"] + b"\x00" * (1024 * 1024), "a.mp3", tamano_max=1024 * 1024)
    with pytest.raises(ValueError, match="Formato de audio no permitido"):
        validar_audio(b"%PDF-1.7 ...", "trampa.mp3", tamano_max=1024)


def test_enviar_audio_por_el_chat():
    chats, imgs, reloj, cid = _chat()
    h = EnviarMensajeHandler(chats, imgs, reloj)
    r = correr(h.handle("autor", "ana", cid, MensajeEntrante(documento=AUDIOS["ogg"], documento_nombre="nota.ogg",
                                                             es_audio=True)))
    assert r.documento.tipo == "ogg" and r.documento.nombre == "nota.ogg"
    assert r.documento.url == f"/api/chats/{cid}/mensajes/{r.id}/documento"
    assert chats.mensajes[r.id].documento.referencia in imgs.objetos


def test_el_campo_audio_no_acepta_documentos():
    chats, imgs, reloj, cid = _chat()
    h = EnviarMensajeHandler(chats, imgs, reloj)
    with pytest.raises(ErrorValidacion, match="Formato de audio no permitido") as e:
        correr(h.handle("autor", "ana", cid, MensajeEntrante(documento=b"%PDF-1.7 x", documento_nombre="a.pdf",
                                                             es_audio=True)))
    assert e.value.extra["campo"] == "audio" and e.value.codigo == "audio_invalido" and not imgs.objetos


# --- Range (reproducir en WebKit) ----------------------------------------------------------------------
def _app_rango(contenido: bytes) -> TestClient:
    app = FastAPI()

    @app.get("/archivo")
    async def archivo(request: Request):
        return respuesta_con_rango(request, contenido, "audio/mpeg", {})

    return TestClient(app)


def test_respuesta_con_rango():
    c = _app_rango(b"0123456789")
    completo = c.get("/archivo")
    assert completo.status_code == 200 and completo.headers["accept-ranges"] == "bytes"
    parte = c.get("/archivo", headers={"Range": "bytes=2-5"})
    assert parte.status_code == 206 and parte.content == b"2345" and parte.headers["content-range"] == "bytes 2-5/10"
    assert c.get("/archivo", headers={"Range": "bytes=7-"}).content == b"789"
    assert c.get("/archivo", headers={"Range": "bytes=-3"}).content == b"789"
    assert c.get("/archivo", headers={"Range": "bytes=50-60"}).status_code == 416


# --- Ubicación en vivo (CU-22) ------------------------------------------------------------------------
def _ubicacion():
    chats, _, reloj, cid = _chat()
    ubicaciones = FakeUbicacionRepository()
    return CompartirUbicacionHandler(chats, ubicaciones, reloj), chats, ubicaciones, reloj, cid


def _posicion(lat=-9.2963, lng=-75.9981):
    return PosicionEntrante(tipo="posicion", lat=lat, lng=lng, precision=15)


def test_solo_participantes_de_un_chat_activo():
    h, _, _, reloj, cid = _ubicacion()
    assert correr(h.chat_permitido("autor", cid)) is not None
    assert correr(h.chat_permitido("intruso", cid)) is None
    assert correr(h.chat_permitido("autor", "no-existe")) is None
    reloj.avanzar(hours=24)
    assert correr(h.chat_permitido("autor", cid)) is None  # chat expirado


def test_la_otra_persona_ve_la_ubicacion_hasta_que_se_detiene():
    h, _, ubicaciones, _, cid = _ubicacion()
    chat = correr(h.chat_permitido("autor", cid))
    correr(h.guardar(chat, "autor", "ana", _posicion()))
    correr(h.guardar(chat, "autor", "ana", _posicion(lat=-9.3)))  # se reemplaza: no hay historial
    assert len(ubicaciones.ubicaciones) == 1
    vista = correr(h.de_la_otra_persona(chat, "lector"))
    assert (vista.nickname, vista.lat) == ("ana", -9.3)
    assert correr(h.de_la_otra_persona(chat, "autor")) is None  # la propia no se envía de vuelta
    correr(h.detener(cid, "autor"))
    assert correr(h.de_la_otra_persona(chat, "lector")) is None


def test_ubicacion_sin_actualizar_vence_a_los_2_minutos():
    h, _, _, reloj, cid = _ubicacion()
    chat = correr(h.chat_permitido("autor", cid))
    correr(h.guardar(chat, "autor", "ana", _posicion()))
    reloj.avanzar(minutes=2)
    assert correr(h.de_la_otra_persona(chat, "lector")) is None


@pytest.mark.parametrize("datos", [{"lat": 91, "lng": 0}, {"lat": 0, "lng": -181}, {"lat": "x", "lng": 0}])
def test_rechaza_coordenadas_invalidas(datos):
    with pytest.raises(ValueError):
        PosicionEntrante(tipo="posicion", precision=10, **datos)
