"""EA-03 — Limpieza física de chats expirados."""
import asyncio
from datetime import timedelta

from app.jobs.ea03_limpiar_chats_expirados.handler import LimpiarChatsExpiradosHandler
from app.shared.domain.entities import Chat, ImagenAdjunta, Mensaje
from tests.fakes import FakeChatRepository, FakeClock, FakeImageStorage, imagen


def _chat(chats, imgs, reloj, respondedor):
    ahora = reloj.ahora()
    referencia = asyncio.run(imgs.guardar(imagen(), "image/png"))
    return asyncio.run(chats.crear_con_primer_mensaje(
        Chat("", f"p_{respondedor}", "autor", respondedor, ahora, ahora, ahora + timedelta(hours=24)),
        Mensaje("", "", respondedor, "n", ahora, imagen=ImagenAdjunta(referencia, "image/png", 9)))), referencia


def test_elimina_solo_chats_expirados_con_mensajes_e_imagenes():
    chats, imgs, reloj = FakeChatRepository(), FakeImageStorage(), FakeClock()
    viejo, img_vieja = _chat(chats, imgs, reloj, "a")
    reloj.avanzar(hours=2)
    vigente, img_vigente = _chat(chats, imgs, reloj, "b")
    reloj.avanzar(hours=22)  # «viejo» cumple 24 h sin mensajes
    resultado = asyncio.run(LimpiarChatsExpiradosHandler(chats, imgs, reloj).handle())
    assert resultado == {"chats_eliminados": 1, "imagenes_eliminadas": 1}
    assert list(chats.chats) == [vigente] and img_vieja not in imgs.objetos and img_vigente in imgs.objetos
    assert all(m.chat_id == vigente for m in chats.mensajes.values())


def test_sin_expirados_no_hace_nada():
    chats, imgs, reloj = FakeChatRepository(), FakeImageStorage(), FakeClock()
    _chat(chats, imgs, reloj, "a")
    assert asyncio.run(LimpiarChatsExpiradosHandler(chats, imgs, reloj).handle())["chats_eliminados"] == 0


def test_cron_exige_secreto(monkeypatch):
    from fastapi.testclient import TestClient

    from app.jobs.ea03_limpiar_chats_expirados import endpoint
    from app.main import app

    chats, imgs, reloj = FakeChatRepository(), FakeImageStorage(), FakeClock()
    app.dependency_overrides[endpoint.get_handler] = lambda: LimpiarChatsExpiradosHandler(chats, imgs, reloj)
    cliente, ruta = TestClient(app), "/jobs/ea03-limpiar-chats-expirados"
    try:
        monkeypatch.delenv("CRON_SECRET", raising=False)
        assert cliente.get(ruta, headers={"Authorization": "Bearer "}).status_code == 401  # sin secreto configurado
        monkeypatch.setenv("CRON_SECRET", "s3cr3t")
        assert cliente.get(ruta).status_code == 401
        assert cliente.get(ruta, headers={"Authorization": "Bearer malo"}).status_code == 401
        respuesta = cliente.get(ruta, headers={"Authorization": "Bearer s3cr3t"})
        assert respuesta.status_code == 200 and respuesta.json()["chats_eliminados"] == 0
    finally:
        app.dependency_overrides.clear()
