"""RNF-SEG-03 (HTTPS y HSTS), RNF-MAN-02 (reloj de pruebas), RNF-FIA-02 (plazos al arrancar) y RNF-PRI-05
(los registros técnicos no guardan el texto ni las imágenes de los chats)."""
import asyncio
import io
import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.shared import clock
from app.shared.web.https import HSTS

SECRETO = {"Authorization": "Bearer s3cr3t"}


# --- RNF-SEG-03 ------------------------------------------------------------------------------
@pytest.fixture
def produccion(monkeypatch):
    monkeypatch.setenv("ENTORNO", "produccion")


@pytest.mark.parametrize("ruta", ["/login", "/terminos?x=1", "/api/terminos"])
def test_http_se_redirige_a_https_en_produccion(produccion, ruta):
    r = TestClient(app, base_url="http://banca.example").get(ruta, follow_redirects=False)
    assert r.status_code == 308 and r.headers["location"] == f"https://banca.example{ruta}"


def test_proxy_que_termina_tls_x_forwarded_proto(produccion):
    cliente = TestClient(app, base_url="https://banca.example")
    r = cliente.get("/api/terminos", headers={"X-Forwarded-Proto": "http"}, follow_redirects=False)
    assert r.status_code == 308 and r.headers["location"] == "https://banca.example/api/terminos"
    r = cliente.get("/api/terminos", headers={"X-Forwarded-Proto": "https"})
    assert r.status_code == 200 and r.headers["strict-transport-security"] == HSTS


def test_fuera_de_produccion_no_redirige_ni_agrega_hsts(monkeypatch):
    monkeypatch.setenv("ENTORNO", "desarrollo")
    r = TestClient(app, base_url="http://localhost").get("/api/terminos")
    assert r.status_code == 200 and "strict-transport-security" not in r.headers


# --- RNF-MAN-02 ------------------------------------------------------------------------------
@pytest.fixture
def entorno_de_pruebas(monkeypatch):
    monkeypatch.setenv("ENTORNO", "pruebas")
    monkeypatch.setenv("CRON_SECRET", "s3cr3t")
    clock.reloj_de_pruebas().reiniciar()
    yield TestClient(app)
    clock.reloj_de_pruebas().reiniciar()


def test_reloj_de_pruebas_se_adelanta(entorno_de_pruebas):
    cliente = entorno_de_pruebas
    assert isinstance(clock.get_clock(), clock.RelojDePruebas)
    antes = clock.get_clock().ahora()
    r = cliente.post("/pruebas/reloj/avanzar", json={"horas": 24}, headers=SECRETO)
    assert r.status_code == 200 and r.json()["desfase_segundos"] == 24 * 3600
    assert clock.get_clock().ahora() - antes >= timedelta(hours=24)
    cliente.post("/pruebas/reloj/avanzar", json={"dias": 3}, headers=SECRETO)
    assert cliente.get("/pruebas/reloj", headers=SECRETO).json()["desfase_segundos"] == (24 + 72) * 3600
    assert cliente.post("/pruebas/reloj/reiniciar", headers=SECRETO).json()["desfase_segundos"] == 0
    with pytest.raises(ValueError):
        clock.reloj_de_pruebas().avanzar(timedelta(hours=-1))  # no se puede retroceder


def test_reloj_de_pruebas_exige_el_secreto(entorno_de_pruebas):
    assert entorno_de_pruebas.post("/pruebas/reloj/avanzar", json={"horas": 1}).status_code == 401
    assert entorno_de_pruebas.post("/pruebas/reloj/avanzar", json={"horas": 1},
                                   headers={"Authorization": "Bearer otro"}).status_code == 401
    assert entorno_de_pruebas.post("/pruebas/reloj/avanzar", json={"horas": -1}, headers=SECRETO).status_code == 422


@pytest.mark.parametrize("entorno", ["desarrollo", "produccion"])
def test_reloj_de_pruebas_no_existe_fuera_del_entorno_de_pruebas(monkeypatch, entorno):
    monkeypatch.setenv("ENTORNO", entorno)
    monkeypatch.setenv("CRON_SECRET", "s3cr3t")
    assert isinstance(clock.get_clock(), clock.SystemClock)
    cliente = TestClient(app, base_url="https://testserver")
    assert cliente.post("/pruebas/reloj/avanzar", json={"horas": 24}, headers=SECRETO).status_code == 404
    assert cliente.get("/pruebas/reloj", headers=SECRETO).status_code == 404


# --- RNF-FIA-02 ------------------------------------------------------------------------------
def test_el_arranque_programa_los_plazos_vencidos(monkeypatch):
    import app.main as principal

    llamadas = []

    async def sin_indices():
        return None

    monkeypatch.setattr(principal, "asegurar_indices_una_vez", sin_indices)
    monkeypatch.setattr(principal, "programar_al_arrancar", lambda: llamadas.append("plazos"))
    with TestClient(app):
        pass
    assert llamadas == ["plazos"]


def test_sin_base_configurada_no_hace_nada(monkeypatch):
    from app.jobs.arranque import aplicar_plazos_vencidos

    monkeypatch.delenv("MONGO_URI", raising=False)
    assert asyncio.run(aplicar_plazos_vencidos()) == {}


# --- RNF-PRI-05 ------------------------------------------------------------------------------
def test_registros_tecnicos_sin_texto_ni_imagenes_de_chats(caplog):
    """Se envían mensajes de texto e imágenes, se reporta el chat y se fuerza un error en la limpieza
    (log.exception): ningún registro contiene el texto ni los bytes de las imágenes."""
    from app.features.m04_chat.cu10_responder_publicacion import endpoint as cu10
    from app.features.m04_chat.cu10_responder_publicacion.handler import ResponderPublicacionHandler
    from app.features.m04_chat.cu11_enviar_mensaje import endpoint as cu11
    from app.features.m04_chat.cu11_enviar_mensaje.handler import EnviarMensajeHandler
    from app.features.m05_reportes.cu14_reportar_chat import endpoint as cu14
    from app.features.m05_reportes.cu14_reportar_chat.handler import ReportarChatHandler
    from app.jobs.ea03_limpiar_chats_expirados.handler import LimpiarChatsExpiradosHandler
    from app.shared.domain.entities import Publicacion, TipoPublicacion
    from app.shared.security.session import SesionActual, get_sesion_actual
    from tests.fakes import (FakeChatRepository, FakeClock, FakeConfig, FakeImageStorage, FakePublicationRepository,
                             FakeReportRepository)

    pubs, chats, imgs, reportes, reloj = (FakePublicationRepository(), FakeChatRepository(), FakeImageStorage(),
                                          FakeReportRepository(), FakeClock())
    ahora = reloj.ahora()
    pid = asyncio.run(pubs.crear(Publicacion("", "autor", "ana", TipoPublicacion.OFREZCO, "t", "d", ahora,
                                             ahora + timedelta(hours=24))))
    sesion = {"actual": SesionActual("s1", "lector", "beto")}
    app.dependency_overrides.update({
        get_sesion_actual: lambda: sesion["actual"],
        cu10.get_handler: lambda: ResponderPublicacionHandler(pubs, chats, imgs, reloj),
        cu11.get_handler: lambda: EnviarMensajeHandler(chats, imgs, reloj),
        cu14.get_handler: lambda: ReportarChatHandler(chats, reportes, imgs, FakeConfig(), reloj),
    })
    secreto = "TEXTO-PRIVADO-PRI05 mi dirección es Jr. Falsa 123"
    foto = io.BytesIO()
    Image.new("RGB", (8, 8), (12, 34, 56)).save(foto, "PNG")
    try:
        with caplog.at_level(logging.DEBUG):
            c = TestClient(app)
            chat = c.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": secreto}).json()["chat_id"]
            assert c.post(f"/api/chats/{chat}/mensajes", files={"imagen": ("f.png", foto.getvalue(), "image/png")}
                          ).status_code == 201
            sesion["actual"] = SesionActual("s2", "autor", "ana")
            assert c.post(f"/api/chats/{chat}/mensajes", data={"texto": secreto + " (respuesta)"}).status_code == 201
            assert c.post(f"/api/chats/{chat}/reportes", json={"codigo_motivo": "SPAM"}).status_code == 201

            async def falla(_):
                raise OSError("almacenamiento no disponible")

            imgs.eliminar = falla  # fuerza log.exception en la limpieza
            reloj.avanzar(hours=25)
            asyncio.run(LimpiarChatsExpiradosHandler(chats, imgs, reloj).handle())
    finally:
        app.dependency_overrides.clear()
    registro = caplog.text + "".join(str(r.args) for r in caplog.records)
    assert "No se pudo eliminar una imagen de chat expirado" in registro  # sí hubo registros, incluido el error
    assert "TEXTO-PRIVADO-PRI05" not in registro and "Jr. Falsa" not in registro
    assert "PNG" not in registro and "\\x89" not in registro  # ni bytes de imagen
