"""M05 — Confidencialidad de los reportes (RF-REP-11, RF-REP-15).

- RF-REP-11: la aplicación no ofrece funciones para consultar, revisar, sancionar ni eliminar reportes.
- RF-REP-15: nadie (ni el reportado ni terceros) puede saber que existe un reporte ni quién reportó.
"""
import asyncio
from datetime import timedelta

from fastapi.routing import APIRoute

from app.features.m02_publicaciones.cu06_ver_mis_publicaciones.handler import VerMisPublicacionesHandler
from app.features.m03_feed.cu08_consultar_feed.handler import ConsultarFeedHandler
from app.features.m03_feed.cu08_consultar_feed.request import ConsultarFeedRequest
from app.features.m03_feed.cu09_ver_detalle_publicacion.handler import VerDetallePublicacionHandler
from app.features.m04_chat.cu12_ver_mis_chats.handler import VerMisChatsHandler
from app.features.m05_reportes.cu13_reportar_publicacion.handler import ReportarPublicacionHandler
from app.features.m05_reportes.cu13_reportar_publicacion.request import ReporteRequest as ReportePublicacion
from app.features.m05_reportes.cu14_reportar_chat.handler import ReportarChatHandler
from app.features.m05_reportes.cu14_reportar_chat.request import ReporteRequest as ReporteChat
from app.main import app
from app.shared.domain.entities import Chat, Mensaje, Publicacion, TipoPublicacion
from tests.fakes import (FakeChatRepository, FakeClock, FakeConfig, FakeImageStorage, FakePublicationRepository,
                         FakeReportRepository)


def _rutas(rutas=None) -> list[tuple[str, set[str]]]:
    """Todas las rutas HTTP, incluidas las páginas fuera del esquema OpenAPI y los routers incluidos."""
    encontradas = []
    for r in app.routes if rutas is None else rutas:
        if isinstance(r, APIRoute) or (hasattr(r, "path") and hasattr(r, "methods") and r.methods):
            encontradas.append((r.path, set(r.methods) - {"HEAD"}))
        elif hasattr(r, "original_router"):
            encontradas += _rutas(r.original_router.routes)
    return encontradas


def test_sin_funciones_de_gestion_de_reportes():
    """RF-REP-11 / RN-37: solo existen las rutas para crear un reporte y los formularios para hacerlo."""
    con_reportes = [(p, m) for p, m in _rutas() if "report" in p.lower()]
    assert sorted(con_reportes) == sorted([
        ("/api/chats/{chat_id}/reportes", {"POST"}),
        ("/api/publicaciones/{publicacion_id}/reportes", {"POST"}),
        ("/chats/{chat_id}/reportar", {"GET"}),
        ("/publicaciones/{publicacion_id}/reportar", {"GET"}),
        ("/jobs/ea05-depurar-contenido-reportado", {"GET"}),  # purga automática, exige CRON_SECRET (RN-26)
    ])
    # Ninguna ruta permite leer, modificar ni borrar reportes o su contenido conservado
    assert not any(m & {"PUT", "PATCH", "DELETE"} for p, m in con_reportes)
    assert not any(p.startswith(("/api/reportes", "/reportes", "/admin")) for p, _ in _rutas())
    # La única ruta que entrega imágenes resuelve mensajes de un chat, no claves del área de retención
    imagenes = [p for p, _ in _rutas() if "imagen" in p]
    assert imagenes == ["/api/chats/{chat_id}/mensajes/{mensaje_id}/imagen"]


def _vistas_publicacion(pubs, chats, reloj, usuario, pid):
    feed = asyncio.run(ConsultarFeedHandler(pubs, reloj).handle(usuario, ConsultarFeedRequest()))
    detalle = asyncio.run(VerDetallePublicacionHandler(pubs, chats, reloj).handle(usuario, pid))
    mias = asyncio.run(VerMisPublicacionesHandler(pubs, reloj).handle(usuario))
    return feed.model_dump(), detalle.model_dump(), mias.model_dump()


def test_reporte_de_publicacion_invisible_para_el_reportado_y_terceros():
    """RF-REP-15 / RN-36: las vistas del autor reportado y de un tercero no cambian tras el reporte."""
    pubs, chats, reportes, reloj = FakePublicationRepository(), FakeChatRepository(), FakeReportRepository(), FakeClock()
    ahora = reloj.ahora()
    pid = asyncio.run(pubs.crear(Publicacion("", "autor", "ana", TipoPublicacion.OFREZCO, "Vendo", "Barato", ahora,
                                             ahora + timedelta(hours=24))))
    antes = {u: _vistas_publicacion(pubs, chats, reloj, u, pid) for u in ("autor", "tercero")}

    respuesta = asyncio.run(ReportarPublicacionHandler(pubs, reportes, FakeConfig(), reloj).handle(
        "lector", pid, ReportePublicacion(codigo_motivo="SPAM", observacion="estafa")))

    assert respuesta.model_dump() == {"mensaje": "Reporte registrado. Gracias por avisar"}  # sin ids ni datos
    assert len(reportes.reportes) == 1
    for usuario in ("autor", "tercero"):
        assert _vistas_publicacion(pubs, chats, reloj, usuario, pid) == antes[usuario]
        texto = str(antes[usuario])
        assert "lector" not in texto and "estafa" not in texto and "SPAM" not in texto


def test_reporte_de_chat_invisible_para_el_otro_participante():
    """RF-REP-15 / RN-36: el interlocutor reportado no ve ningún cambio en su lista ni en el chat."""
    chats, reportes, imgs, reloj = FakeChatRepository(), FakeReportRepository(), FakeImageStorage(), FakeClock()
    ahora = reloj.ahora()
    cid = asyncio.run(chats.crear_con_primer_mensaje(
        Chat("", "p1", "autor", "lector", ahora, ahora, ahora + timedelta(hours=24), TipoPublicacion.NECESITO, "t",
             nickname_autor="ana", nickname_respondedor="beto"),
        Mensaje("", "", "lector", "beto", ahora, texto="hola")))
    ver = VerMisChatsHandler(chats, imgs, FakeConfig(), reloj)
    asyncio.run(ver.abrir("autor", cid))  # deja el chat leído, para que el antes/después sea comparable
    antes = (asyncio.run(ver.handle("autor")).model_dump(), asyncio.run(ver.abrir("autor", cid)).model_dump())

    asyncio.run(ReportarChatHandler(chats, reportes, imgs, FakeConfig(), reloj).handle(
        "lector", cid, ReporteChat(codigo_motivo="HARASSMENT")))

    despues = (asyncio.run(ver.handle("autor")).model_dump(), asyncio.run(ver.abrir("autor", cid)).model_dump())
    assert len(reportes.reportes) == 1 and despues == antes
