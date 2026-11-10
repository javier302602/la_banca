"""Criterios de RNF-FIA-02 (recuperación tras una caída) y RNF-MAN-02 (reloj de pruebas) contra MongoDB real."""
import time
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.shared import clock
from app.shared.email.sender import get_email_sender

SECRETO = {"Authorization": "Bearer s3cr3t"}


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def _cliente():
    return TestClient(app, base_url="https://testserver")


def _registrar(c, correo, nick, activar=True):
    r = c.post("/api/cuentas", json={"correo": correo, "contrasena": "clave123", "confirmacion": "clave123",
                                     "nickname": nick, "acepta_terminos": True})
    assert r.status_code == 201, r.text
    if activar:
        token = get_email_sender().enviados[-1].enlace.split("token=")[1]
        assert c.post("/api/cuentas/activar", json={"token": token}).status_code == 200


def _entrar(c, correo):
    r = c.post("/api/sesiones", json={"correo": correo, "contrasena": "clave123"})
    assert r.status_code == 200, r.text


def test_fia_02_plazos_vencidos_durante_la_caida_se_aplican_al_arrancar(db):
    """Mientras el servicio está detenido vencen un chat, un reporte y una cuenta pendiente; al restablecerlo se
    eliminan en ≤ 1 min y lo que no venció se mantiene."""
    with _cliente() as c:  # la app en marcha: se registra una cuenta pendiente y luego «se detiene»
        _registrar(c, "pendiente.fia@unas.edu.pe", "pendiente_fia", activar=False)
    # Lo que vence durante la caída se escribe con la app detenida
    ahora = datetime.now(timezone.utc)
    usuario = ObjectId()
    chats = [{"publicationId": ObjectId(), "authorId": usuario, "responderId": ObjectId(),
              "participants": [usuario], "startedAt": ahora - timedelta(hours=30), "lastActivityAt": ahora,
              "expiresAt": vence, "status": "ACTIVE"} for vence in (ahora - timedelta(minutes=10),
                                                                    ahora + timedelta(hours=5))]
    vencido, vigente = db.chats.insert_many(chats).inserted_ids
    db.messages.insert_many([{"chatId": c, "senderId": usuario, "senderNickname": "x", "text": "hola",
                              "imageAttachment": None, "sentAt": ahora} for c in (vencido, vigente)])
    snapshot = {"offenderUserId": usuario, "capturedAt": ahora, "publicationData": None, "messagesSnapshot": [],
                "retainedImageKeys": []}
    reportes = db.reports.insert_many([{"reporterId": ObjectId(), "targetType": "CHAT", "targetId": vencido,
                                        "reasonCode": "SPAM", "reportedAt": ahora - timedelta(days=7, minutes=10),
                                        "retentionEndsAt": fin, "reportedContentSnapshot": snapshot}
                                       for fin in (ahora - timedelta(minutes=10), ahora + timedelta(days=1))]
                                      ).inserted_ids
    db.accounts.update_one({"email": "pendiente.fia@unas.edu.pe"},
                           {"$set": {"createdAt": ahora - timedelta(hours=72, minutes=10)}})

    inicio = time.monotonic()
    with _cliente():  # «restablecimiento»: el lifespan programa la aplicación de los plazos vencidos
        while time.monotonic() - inicio < 60:
            if (not db.chats.find_one({"_id": vencido}) and not db.reports.find_one({"_id": reportes[0]})
                    and not db.accounts.find_one({"email": "pendiente.fia@unas.edu.pe"})):
                break
            time.sleep(0.2)
    transcurrido = time.monotonic() - inicio
    assert transcurrido < 60, "los plazos vencidos no se aplicaron en 1 minuto"
    assert db.messages.count_documents({"chatId": vencido}) == 0
    # lo no vencido se mantiene
    assert db.chats.find_one({"_id": vigente}) and db.messages.count_documents({"chatId": vigente}) == 1
    assert db.reports.find_one({"_id": reportes[1]})


@pytest.fixture
def entorno_de_pruebas(monkeypatch):
    monkeypatch.setenv("ENTORNO", "pruebas")
    clock.reloj_de_pruebas().reiniciar()
    yield
    clock.reloj_de_pruebas().reiniciar()


def test_man_02_adelantar_24_y_72_horas(db, entorno_de_pruebas):
    """Criterio de RNF-MAN-02: se adelanta la hora 24 h y expiran una publicación y un chat sin mensajes nuevos;
    se adelanta 72 h y se elimina una cuenta pendiente de activación."""
    with _cliente() as autor, _cliente() as lector:
        _registrar(autor, "autor.man@unas.edu.pe", "autor_man")
        _registrar(lector, "lector.man@unas.edu.pe", "lector_man")
        _entrar(autor, "autor.man@unas.edu.pe")
        _entrar(lector, "lector.man@unas.edu.pe")
        pid = autor.post("/api/publicaciones", json={"tipo": "NECESITO", "titulo": "Reloj", "descripcion": "x"}).json()["id"]
        chat = lector.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "hola"}).json()["chat_id"]
        assert any(i["id"] == pid for i in lector.get("/api/feed").json()["items"])

        assert autor.post("/pruebas/reloj/avanzar", json={"horas": 24}, headers=SECRETO).status_code == 200
        _entrar(autor, "autor.man@unas.edu.pe")  # las sesiones también vencieron (12 h de inactividad)
        _entrar(lector, "lector.man@unas.edu.pe")
        assert all(i["id"] != pid for i in lector.get("/api/feed").json()["items"])
        assert lector.get(f"/api/publicaciones/{pid}").status_code == 410
        assert lector.get(f"/api/chats/{chat}").status_code == 410

        _registrar(autor, "pendiente.man@unas.edu.pe", "pendiente_man", activar=False)
        assert autor.post("/pruebas/reloj/avanzar", json={"horas": 72}, headers=SECRETO).status_code == 200
        r = autor.get("/jobs/ea07-eliminar-cuentas-no-activadas", headers=SECRETO)
        assert r.status_code == 200 and r.json()["cuentas_eliminadas"] >= 1
        assert not db.accounts.find_one({"email": "pendiente.man@unas.edu.pe"})
