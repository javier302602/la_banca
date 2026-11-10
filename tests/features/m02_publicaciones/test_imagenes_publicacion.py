"""Imágenes en publicaciones (SRS v2.0, Fase 3): CU-05, CU-08, CU-09, CU-13 y EA-03."""
import asyncio
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.features.m02_publicaciones.cu05_crear_publicacion.handler import CrearPublicacionHandler
from app.features.m02_publicaciones.cu05_crear_publicacion.request import CrearPublicacionRequest
from app.features.m03_feed.cu08_consultar_feed.handler import ConsultarFeedHandler
from app.features.m03_feed.cu08_consultar_feed.request import ConsultarFeedRequest
from app.features.m03_feed.cu09_ver_detalle_publicacion.handler import VerDetallePublicacionHandler
from app.features.m05_reportes.cu13_reportar_publicacion.handler import ReportarPublicacionHandler
from app.features.m05_reportes.cu13_reportar_publicacion.request import ReporteRequest
from app.jobs.ea03_limpiar_chats_expirados.handler import LimpiarChatsExpiradosHandler
from app.jobs.ea05_depurar_contenido_reportado.handler import DepurarContenidoReportadoHandler
from app.shared.domain.entities import TAMANO_MAX_IMAGEN
from app.shared.domain.errors import Conflicto, ErrorValidacion, NoDisponible, NoEncontrado
from tests.fakes import (FakeChatRepository, FakeClock, FakeConfig, FakeImageStorage, FakePublicationRepository,
                         FakeReportRepository, imagen)


def correr(c):
    return asyncio.run(c)


def jpeg_con_gps() -> bytes:
    exif = Image.Exif()
    exif[0x8825] = {2: (12, 3, 4)}
    salida = io.BytesIO()
    Image.new("RGB", (64, 48), "red").save(salida, format="JPEG", exif=exif)
    return salida.getvalue()


def req():
    return CrearPublicacionRequest(tipo="OFREZCO", titulo="Calculadora", descripcion="La presto")


@pytest.fixture
def mundo():
    pubs, imgs, reloj, chats, reportes = (FakePublicationRepository(), FakeImageStorage(), FakeClock(),
                                          FakeChatRepository(), FakeReportRepository())
    crear = CrearPublicacionHandler(pubs, FakeConfig(), reloj, imgs)
    return {"pubs": pubs, "imgs": imgs, "reloj": reloj, "chats": chats, "reportes": reportes, "crear": crear,
            "detalle": VerDetallePublicacionHandler(pubs, chats, reloj, imagenes=imgs)}


def test_crea_con_hasta_3_imagenes_sin_exif(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req(), [jpeg_con_gps(), imagen("PNG"), imagen("WEBP")]))
    assert r.imagenes == [f"/api/publicaciones/{r.id}/imagenes/{i}" for i in range(3)]
    p = mundo["pubs"].publicaciones[r.id]
    assert [i.mime_type for i in p.imagenes] == ["image/jpeg", "image/png", "image/webp"]
    assert all(i.referencia.startswith("publicaciones/") for i in p.imagenes)
    with Image.open(io.BytesIO(mundo["imgs"].objetos[p.imagenes[0].referencia])) as limpia:
        assert not limpia.getexif()  # sin GPS ni otros metadatos


def test_sin_imagenes_sigue_funcionando_como_en_v1(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req()))
    assert r.imagenes == [] and mundo["pubs"].publicaciones[r.id].imagenes == []


@pytest.mark.parametrize("imagenes, codigo", [
    ([imagen()] * 4, "demasiadas_imagenes"),
    ([imagen(), b"GIF89a....."], "imagen_invalida"),
    ([b"\xff\xd8\xff" + b"0" * 50], "imagen_invalida"),                 # firma JPEG, contenido dañado
    ([b"\x89PNG\r\n\x1a\n" + b"0" * TAMANO_MAX_IMAGEN], "imagen_invalida"),  # > 5 MB
])
def test_rechaza_imagenes_invalidas_sin_dejar_objetos(mundo, imagenes, codigo):
    with pytest.raises(ErrorValidacion) as error:
        correr(mundo["crear"].handle("u1", "ana", req(), imagenes))
    assert error.value.codigo == codigo and error.value.extra["campo"] == "imagenes"
    assert not mundo["imgs"].objetos and not mundo["pubs"].publicaciones


def test_sin_cupo_no_guarda_imagenes(mundo):
    for _ in range(3):
        correr(mundo["crear"].handle("u1", "ana", req()))
    with pytest.raises(Conflicto):
        correr(mundo["crear"].handle("u1", "ana", req(), [imagen()]))
    assert not mundo["imgs"].objetos


def test_galeria_en_detalle_y_miniatura_en_feed(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req(), [imagen("PNG"), imagen("JPEG")]))
    d = correr(mundo["detalle"].handle("u2", r.id))
    assert d.imagenes == r.imagenes
    descarga = correr(mundo["detalle"].imagen(r.id, 1))
    assert descarga.mime_type == "image/jpeg" and descarga.contenido.startswith(b"\xff\xd8")
    with pytest.raises(NoEncontrado):
        correr(mundo["detalle"].imagen(r.id, 2))
    item = correr(ConsultarFeedHandler(mundo["pubs"], mundo["reloj"]).handle("u2", ConsultarFeedRequest())).items[0]
    assert item.num_imagenes == 2 and item.miniatura == r.imagenes[0]


def test_imagen_de_publicacion_vencida_no_se_entrega(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req(), [imagen()]))
    mundo["reloj"].avanzar(hours=24)
    with pytest.raises(NoDisponible):
        correr(mundo["detalle"].imagen(r.id, 0))


def test_reporte_copia_las_imagenes_a_retencion_y_ea03_ea05_limpian(mundo):
    imgs, reloj, reportes = mundo["imgs"], mundo["reloj"], mundo["reportes"]
    r = correr(mundo["crear"].handle("u1", "ana", req(), [imagen(), imagen("JPEG")]))
    originales = [i.referencia for i in mundo["pubs"].publicaciones[r.id].imagenes]
    reportar = ReportarPublicacionHandler(mundo["pubs"], reportes, FakeConfig(), reloj, imgs)
    correr(reportar.handle("u2", r.id, ReporteRequest(codigo_motivo="SPAM")))
    contenido = next(iter(reportes.reportes.values())).contenido
    retenidas = contenido.snapshot_imagenes
    assert len(retenidas) == 2 and all(k.startswith("reports/") for k in retenidas)
    assert contenido.datos_publicacion["imageKeys"] == retenidas

    # EA-03: vencida la publicación, sus imágenes se borran; las retenidas siguen
    reloj.avanzar(hours=24)
    ea03 = LimpiarChatsExpiradosHandler(mundo["chats"], imgs, reloj, mundo["pubs"])
    assert correr(ea03.handle())["imagenes_de_publicaciones_eliminadas"] == 2
    assert not any(k in imgs.objetos for k in originales) and all(k in imgs.objetos for k in retenidas)
    assert correr(ea03.handle())["imagenes_de_publicaciones_eliminadas"] == 0  # idempotente

    # EA-05: vencido el plazo de conservación, también las retenidas
    reloj.avanzar(days=7)
    correr(DepurarContenidoReportadoHandler(reportes, imgs, reloj).handle())
    assert not imgs.objetos


def test_si_el_reporte_falla_no_quedan_copias(mundo):
    r = correr(mundo["crear"].handle("u1", "ana", req(), [imagen()]))

    class Rota(FakeReportRepository):
        async def crear(self, reporte):
            raise RuntimeError("base caída")

    reportar = ReportarPublicacionHandler(mundo["pubs"], Rota(), FakeConfig(), mundo["reloj"], mundo["imgs"])
    with pytest.raises(RuntimeError):
        correr(reportar.handle("u2", r.id, ReporteRequest(codigo_motivo="SPAM")))
    assert list(mundo["imgs"].objetos) == [mundo["pubs"].publicaciones[r.id].imagenes[0].referencia]


def test_endpoint_multipart_y_json(monkeypatch):
    """La API acepta JSON (como v1) o multipart con «imagenes»; los errores llegan en español con su campo."""
    from app.features.m02_publicaciones.cu05_crear_publicacion import endpoint
    from app.main import app
    from app.shared.security.session import SesionActual, get_sesion_actual

    pubs, imgs = FakePublicationRepository(), FakeImageStorage()
    app.dependency_overrides[endpoint.get_handler] = lambda: CrearPublicacionHandler(pubs, FakeConfig(), FakeClock(), imgs)
    app.dependency_overrides[get_sesion_actual] = lambda: SesionActual("s1", "u1", "ana")
    try:
        c = TestClient(app)
        r = c.post("/api/publicaciones", json={"tipo": "NECESITO", "titulo": "t", "descripcion": "d"})
        assert r.status_code == 201 and r.json()["imagenes"] == []
        archivos = [("imagenes", (f"{i}.png", imagen(), "image/png")) for i in range(2)]
        r = c.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "t", "descripcion": "d"}, files=archivos)
        assert r.status_code == 201 and len(r.json()["imagenes"]) == 2
        r = c.post("/api/publicaciones", data={"titulo": "t", "descripcion": "d"}, files=archivos[:1])
        assert r.status_code == 422 and r.json()["errores"][0]["campo"] == "tipo"
        muchas = [("imagenes", (f"{i}.png", imagen(), "image/png")) for i in range(5)]
        r = c.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "t", "descripcion": "d"}, files=muchas)
        assert r.status_code == 422 and r.json()["campo"] == "imagenes"
        r = c.post("/api/publicaciones", content=b"{no es json", headers={"Content-Type": "application/json"})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()
