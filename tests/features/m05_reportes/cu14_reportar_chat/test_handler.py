"""CU-14 — Reportar un chat (snapshot + copiar_a_retencion)."""
import asyncio
from datetime import timedelta

import pytest

from app.features.m05_reportes.cu14_reportar_chat.handler import ReportarChatHandler
from app.features.m05_reportes.cu14_reportar_chat.request import ReporteRequest
from app.shared.domain.entities import Chat, ImagenAdjunta, Mensaje, TipoObjetoReportado
from app.shared.domain.errors import NoDisponible, NoEncontrado
from tests.fakes import FakeChatRepository, FakeClock, FakeConfig, FakeImageStorage, FakeReportRepository, imagen


def _escenario():
    chats, reportes, imgs, reloj = FakeChatRepository(), FakeReportRepository(), FakeImageStorage(), FakeClock()
    ahora = reloj.ahora()
    cid = asyncio.run(chats.crear_con_primer_mensaje(
        Chat("", "p1", "autor", "lector", ahora, ahora, ahora + timedelta(hours=24), titulo_publicacion="Apuntes"),
        Mensaje("", "", "lector", "beto", ahora, texto="hola")))
    referencia = asyncio.run(imgs.guardar(imagen(), "image/png"))
    asyncio.run(chats.agregar_mensaje(Mensaje("", cid, "autor", "ana", ahora, imagen=ImagenAdjunta(referencia,
                                                                                                    "image/png", 9)),
                                      ahora + timedelta(hours=24)))
    h = ReportarChatHandler(chats, reportes, imgs, FakeConfig(), reloj)
    return h, chats, reportes, imgs, reloj, cid, referencia


def _reportar(h, cid, usuario="lector"):
    return asyncio.run(h.handle(usuario, cid, ReporteRequest(codigo_motivo="HARASSMENT")))


def test_snapshot_de_textos_e_imagenes_retenidas():
    h, chats, reportes, imgs, _, cid, referencia = _escenario()
    assert _reportar(h, cid).mensaje == "Reporte registrado. Gracias por avisar"
    [r] = reportes.reportes.values()
    assert r.tipo_objeto is TipoObjetoReportado.CHAT and r.contenido.usuario_reportado_id == "autor"
    textos = [m["texto"] for m in r.contenido.snapshot_textos["mensajes"]]
    assert textos == ["hola", None]  # RF-REP-17
    [copia] = r.contenido.snapshot_imagenes
    assert copia.startswith("reports/") and copia != referencia and copia in imgs.objetos
    # EA-03 borra el chat y su imagen original; la copia retenida sobrevive (RF-REP-08)
    for ref in asyncio.run(chats.eliminar_chat(cid)):
        asyncio.run(imgs.eliminar(ref))
    assert referencia not in imgs.objetos and copia in imgs.objetos


def test_reportes_sucesivos_permitidos():
    h, _, reportes, _, reloj, cid, _ = _escenario()
    _reportar(h, cid)
    reloj.avanzar(hours=1)
    _reportar(h, cid)  # RF-REP-16
    plazos = sorted(r.fecha_retencion_fin for r in reportes.reportes.values())
    assert plazos[1] - plazos[0] == timedelta(hours=1)


def test_solo_participantes_de_chat_activo():
    h, _, _, _, reloj, cid, _ = _escenario()
    with pytest.raises(NoEncontrado):
        _reportar(h, cid, usuario="intruso")
    reloj.avanzar(hours=24)
    with pytest.raises(NoDisponible):
        _reportar(h, cid)


def test_fallo_al_registrar_no_deja_copias():
    h, _, reportes, imgs, _, cid, referencia = _escenario()

    async def falla(*_):
        raise RuntimeError("mongo caído")

    reportes.crear = falla
    with pytest.raises(RuntimeError):
        _reportar(h, cid)
    assert list(imgs.objetos) == [referencia]
