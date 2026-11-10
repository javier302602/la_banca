"""Chat estilo Messenger (SRS v2.0, Fase 4): documentos, stickers, «visto», reporte y limpieza."""
import asyncio
import io
import zipfile
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.features.m04_chat.cu11_enviar_mensaje.handler import EnviarMensajeHandler
from app.features.m04_chat.cu11_enviar_mensaje.request import MensajeEntrante
from app.features.m04_chat.cu12_ver_mis_chats.handler import VerMisChatsHandler
from app.features.m04_chat.cu12_ver_mis_chats.request import AbrirChatRequest
from app.features.m05_reportes.cu14_reportar_chat.handler import ReportarChatHandler
from app.features.m05_reportes.cu14_reportar_chat.request import ReporteRequest
from app.jobs.ea03_limpiar_chats_expirados.handler import LimpiarChatsExpiradosHandler
from app.jobs.ea05_depurar_contenido_reportado.handler import DepurarContenidoReportadoHandler
from app.shared.domain import documentos
from app.shared.domain.entities import STICKERS, Chat, Mensaje, TipoPublicacion
from app.shared.domain.errors import ErrorValidacion, NoEncontrado
from tests.fakes import (FakeChatRepository, FakeClock, FakeConfig, FakeImageStorage, FakeReportRepository,
                         imagen)
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]

TIPOS_OOXML = {
    "docx": ("word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
    "xlsx": ("xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"),
    "pptx": ("ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
}


def ooxml(tipo: str, macros: bool = False, sin_tipos: bool = False) -> bytes:
    parte, contenido = TIPOS_OOXML[tipo]
    if macros:
        contenido = contenido.replace(".main+xml", ".macroEnabled.main+xml").replace("sheet.main", "sheet.macroEnabled.main")
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zf:
        if not sin_tipos:
            zf.writestr("[Content_Types].xml",
                        f'<?xml version="1.0"?><Types><Override PartName="/{parte}" ContentType="{contenido}"/></Types>')
        zf.writestr(parte, "<x/>")
        if macros:
            zf.writestr(parte.split("/")[0] + "/vbaProject.bin", b"\x00VBA")
    return salida.getvalue()


PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


# --- Validación por contenido ---------------------------------------------------------------------------------
@pytest.mark.parametrize("contenido, tipo", [
    (PDF, "pdf"), (ooxml("docx"), "docx"), (ooxml("xlsx"), "xlsx"), (ooxml("pptx"), "pptx"),
    ("Apuntes de cálculo\n- límites\r\n\tderivadas\n".encode(), "txt"),
    ("\ufeffcon BOM".encode("utf-8"), "txt"),
])
def test_tipos_permitidos_por_contenido(contenido, tipo):
    assert documentos.detectar_tipo(contenido) == tipo


@pytest.mark.parametrize("contenido, mensaje", [
    (b"", documentos.MSG_VACIO),
    (b"MZ\x90\x00" + b"\x00" * 200, documentos.MSG_EJECUTABLE),            # .exe aunque se llame .pdf
    (b"\x7fELF\x02\x01\x01" + b"\x00" * 50, documentos.MSG_EJECUTABLE),
    (b"\xcf\xfa\xed\xfe" + b"\x00" * 50, documentos.MSG_EJECUTABLE),       # Mach-O
    (b"#!/bin/sh\nrm -rf /\n", documentos.MSG_EJECUTABLE),
    (ooxml("docx", macros=True), documentos.MSG_MACROS),                    # .docm
    (ooxml("xlsx", macros=True), documentos.MSG_MACROS),                    # .xlsm
    (ooxml("pptx", macros=True), documentos.MSG_MACROS),                    # .pptm
    (ooxml("docx", sin_tipos=True), documentos.MSG_FORMATO),                # ZIP cualquiera
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100, documentos.MSG_FORMATO),  # .doc/.xls antiguos (OLE)
    (b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, documentos.MSG_FORMATO),           # binario: no es UTF-8 válido
    (b"texto con \x00 nulo", documentos.MSG_FORMATO),
    (b"PK\x03\x04roto", documentos.MSG_DANADO),
    (b"%PDF-" + b"0" * documentos.TAMANO_MAX_DOCUMENTO, documentos.MSG_GRANDE),
])
def test_rechazados(contenido, mensaje):
    with pytest.raises(ValueError, match=mensaje.replace("(", r"\(").replace(")", r"\)").replace(".", r"\.")):
        documentos.detectar_tipo(contenido)


def test_zip_con_dos_partes_principales_no_se_acepta():
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<x/>")
        zf.writestr("xl/workbook.xml", "<x/>")
    with pytest.raises(ValueError):
        documentos.detectar_tipo(salida.getvalue())


@pytest.mark.parametrize("original, tipo, esperado", [
    ("informe final.pdf", "pdf", "informe final.pdf"),
    ("virus.exe", "pdf", "virus.pdf"),                     # la extensión sale del contenido
    ("../../etc/passwd", "txt", "passwd.txt"),
    ("C:\\Users\\x\\notas.TXT", "txt", "notas.txt"),
    ("a\x00b\u202e.docx", "docx", "ab.docx"),               # sin caracteres de control ni de dirección
    ("", "xlsx", "documento.xlsx"), (None, "pptx", "documento.pptx"),
    ("x" * 300 + ".pdf", "pdf", "x" * 96 + ".pdf"),
])
def test_nombre_seguro(original, tipo, esperado):
    assert documentos.nombre_seguro(original, tipo) == esperado


# --- CU-11 / CU-12 ---------------------------------------------------------------------------------------------
def correr(c):
    return asyncio.run(c)


@pytest.fixture
def chat():
    chats, imgs, reloj = FakeChatRepository(), FakeImageStorage(), FakeClock()
    ahora = reloj.ahora()
    cid = correr(chats.crear_con_primer_mensaje(
        Chat("", "p1", "autor", "lector", ahora, ahora, ahora + timedelta(hours=24), TipoPublicacion.OFREZCO, "Libro",
             nickname_autor="ana", nickname_respondedor="beto", ultima_lectura={"lector": ahora}),
        Mensaje("", "", "lector", "beto", ahora, texto="hola")))
    return {"chats": chats, "imgs": imgs, "reloj": reloj, "cid": cid,
            "enviar": EnviarMensajeHandler(chats, imgs, reloj), "ver": VerMisChatsHandler(chats, imgs, FakeConfig(), reloj)}


def test_solo_un_contenido_por_mensaje():
    for datos in ({"texto": "hola", "sticker": "sticker-01"}, {"sticker": "sticker-02", "documento": PDF},
                  {"imagen": imagen(), "documento": PDF}, {}):
        with pytest.raises(ValidationError):
            MensajeEntrante(**datos)
    with pytest.raises(ValidationError):
        MensajeEntrante(sticker="sticker-21")
    assert len(STICKERS) == 20
    for s in STICKERS:
        svg = (RAIZ / "web/static/stickers" / f"{s}.svg").read_text(encoding="utf-8")
        assert svg.startswith("<svg") and "<script" not in svg and "<image" not in svg and "http" not in svg.replace(
            "http://www.w3.org/2000/svg", "")


def test_enviar_sticker(chat):
    m = correr(chat["enviar"].handle("autor", "ana", chat["cid"], MensajeEntrante(sticker="sticker-07")))
    assert m.sticker == "sticker-07" and m.sticker_url == "/static/stickers/sticker-07.svg" and m.texto is None
    abierto = correr(chat["ver"].abrir("lector", chat["cid"]))
    assert abierto.mensajes[-1].sticker_url == "/static/stickers/sticker-07.svg"


def test_enviar_documento_y_descargarlo_solo_participantes(chat):
    m = correr(chat["enviar"].handle("autor", "ana", chat["cid"],
                                     MensajeEntrante(documento=ooxml("xlsx"), documento_nombre="notas.xls")))
    assert m.documento.nombre == "notas.xlsx" and m.documento.tipo == "xlsx"
    assert m.documento.url == f"/api/chats/{chat['cid']}/mensajes/{m.id}/documento"
    [clave] = [k for k in chat["imgs"].objetos]
    assert clave.startswith("documentos/") and clave.endswith(".xlsx")
    d = correr(chat["ver"].documento("lector", chat["cid"], m.id))
    assert d.nombre == "notas.xlsx" and d.contenido == ooxml("xlsx") or d.contenido.startswith(b"PK")
    with pytest.raises(NoEncontrado):
        correr(chat["ver"].documento("intruso", chat["cid"], m.id))


def test_documento_invalido_no_se_guarda(chat):
    with pytest.raises(ErrorValidacion) as error:
        correr(chat["enviar"].handle("autor", "ana", chat["cid"],
                                     MensajeEntrante(documento=ooxml("docx", macros=True), documento_nombre="x.docx")))
    assert error.value.extra["campo"] == "documento" and "macros" in error.value.mensaje
    assert not chat["imgs"].objetos


def test_visto_usa_last_read_at_de_la_otra_persona(chat):
    chats, reloj, cid = chat["chats"], chat["reloj"], chat["cid"]
    reloj.avanzar(minutes=1)
    m = correr(chat["enviar"].handle("autor", "ana", cid, MensajeEntrante(texto="¿sigue disponible?")))
    antes = correr(chat["ver"].abrir("autor", cid, AbrirChatRequest(despues_de=m.fecha_envio)))
    assert antes.visto_hasta is not None and antes.visto_hasta < m.fecha_envio  # «Enviado»
    reloj.avanzar(minutes=1)
    correr(chat["ver"].abrir("lector", cid))  # la otra persona abre el chat
    despues = correr(chat["ver"].abrir("autor", cid, AbrirChatRequest(despues_de=m.fecha_envio)))
    assert despues.visto_hasta >= m.fecha_envio  # «Visto»


def test_reporte_conserva_documentos_y_ea03_ea05_los_borran(chat):
    chats, imgs, reloj, cid = chat["chats"], chat["imgs"], chat["reloj"], chat["cid"]
    m = correr(chat["enviar"].handle("autor", "ana", cid, MensajeEntrante(documento=PDF, documento_nombre="guia.pdf")))
    correr(chat["enviar"].handle("lector", "beto", cid, MensajeEntrante(sticker="sticker-20")))
    original = next(iter(imgs.objetos))
    reportes = FakeReportRepository()
    correr(ReportarChatHandler(chats, reportes, imgs, FakeConfig(), reloj).handle(
        "lector", cid, ReporteRequest(codigo_motivo="SPAM")))
    contenido = next(iter(reportes.reportes.values())).contenido
    doc = next(x for x in contenido.mensajes if x["document"])["document"]
    assert doc["fileName"] == "guia.pdf" and doc["key"].startswith("reports/") and doc["key"] in imgs.objetos
    assert any(x["sticker"] == "sticker-20" for x in contenido.mensajes)
    assert doc["key"] in contenido.snapshot_imagenes
    reloj.avanzar(hours=25)
    correr(LimpiarChatsExpiradosHandler(chats, imgs, reloj).handle())
    assert original not in imgs.objetos and doc["key"] in imgs.objetos
    reloj.avanzar(days=7)
    correr(DepurarContenidoReportadoHandler(reportes, imgs, reloj).handle())
    assert not imgs.objetos
    assert m.documento is not None


def test_endpoint_documento_con_cabeceras_seguras(chat):
    from app.features.m04_chat.cu11_enviar_mensaje import endpoint as e11
    from app.features.m04_chat.cu12_ver_mis_chats import endpoint as e12
    from app.main import app
    from app.shared.security.session import SesionActual, get_sesion_actual

    app.dependency_overrides[e11.get_handler] = lambda: chat["enviar"]
    app.dependency_overrides[e12.get_handler] = lambda: chat["ver"]
    app.dependency_overrides[get_sesion_actual] = lambda: SesionActual("s", "autor", "ana")
    try:
        c = TestClient(app)
        r = c.post(f"/api/chats/{chat['cid']}/mensajes",
                   files={"documento": ("Guía «final».pdf", PDF, "application/octet-stream")})
        assert r.status_code == 201, r.text
        url = r.json()["documento"]["url"]
        r = c.get(url)
        assert r.status_code == 200 and r.content == PDF
        assert r.headers["content-type"] == "application/pdf"
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["content-disposition"].startswith("attachment;")
        assert "filename*=UTF-8''Gu%C3%ADa%20%C2%ABfinal%C2%BB.pdf" in r.headers["content-disposition"]
        r = c.post(f"/api/chats/{chat['cid']}/mensajes", files={"documento": ("x.pdf", b"MZ" + b"\0" * 64, "application/pdf")})
        assert r.status_code == 422 and r.json()["campo"] == "documento"
        r = c.post(f"/api/chats/{chat['cid']}/mensajes", data={"sticker": "sticker-03"})
        assert r.status_code == 201 and r.json()["sticker_url"].endswith("sticker-03.svg")
        txt = c.post(f"/api/chats/{chat['cid']}/mensajes", files={"documento": ("n.txt", "<script>x</script>".encode(), "text/html")})
        r = c.get(txt.json()["documento"]["url"])
        assert r.headers["content-type"] == "text/plain; charset=utf-8" and r.headers["content-disposition"].startswith("attachment")
    finally:
        app.dependency_overrides.clear()
