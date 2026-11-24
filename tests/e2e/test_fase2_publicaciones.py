"""Fase 2 contra MongoDB real: índices TTL de 30 días, video, reacciones (aggregate) y ocultar al vencer."""
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.shared.email.sender import get_email_sender

TREINTA_DIAS = 30 * 24 * 3600
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def _entrar(c, correo, nick):
    c.post("/api/cuentas", json={"correo": correo, "contrasena": "clave123", "confirmacion": "clave123",
                                 "nickname": nick, "acepta_terminos": True})
    codigo = get_email_sender().enviados[-1].codigo
    assert c.post("/api/cuentas/activar", json={"correo": correo, "codigo": codigo}).status_code == 200
    assert c.post("/api/sesiones", json={"correo": correo, "contrasena": "clave123"}).status_code == 200


def test_publicaciones_fase2(db):
    with TestClient(app, base_url="https://testserver") as a, TestClient(app, base_url="https://testserver") as b:
        _entrar(a, "autora@unas.edu.pe", "autora")
        _entrar(b, "lector@unas.edu.pe", "lector")

        # Índices TTL: borran 30 días después de vencer (no a las 24 h)
        ttl = {i["name"]: i.get("expireAfterSeconds") for i in db.publications.list_indexes()}
        assert ttl["ttl_publications_retencion"] == TREINTA_DIAS
        assert {i["name"]: i.get("expireAfterSeconds") for i in db.reactions.list_indexes()}[
            "ttl_reactions_retencion"] == TREINTA_DIAS

        # Crear con video (multipart) y descargarlo
        r = a.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "Clase", "descripcion": "Grabada"},
                   files={"video": ("clase.mp4", MP4, "video/mp4")})
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        v = b.get(f"/api/publicaciones/{pid}/video")
        assert v.status_code == 200 and v.content == MP4 and v.headers["content-type"] == "video/mp4"

        # Reacciones: una por estudiante, conteos en feed y detalle
        assert b.put(f"/api/publicaciones/{pid}/reaccion", json={"tipo": "ME_GUSTA"}).json()["total"] == 1
        assert a.put(f"/api/publicaciones/{pid}/reaccion", json={"tipo": "ME_ENCANTA"}).json()["total"] == 2
        r = b.put(f"/api/publicaciones/{pid}/reaccion", json={"tipo": "ME_ENCANTA"}).json()
        assert r == {"conteos": {"ME_ENCANTA": 2}, "total": 2, "mia": "ME_ENCANTA"}
        item = b.get("/api/feed").json()["items"][0]
        assert item["video"] and item["reacciones"]["total"] == 2 and item["extracto"] == "Grabada"
        assert db.reactions.count_documents({"publicationId": ObjectId(pid)}) == 2

        # Al vencer: oculta en feed y detalle, pero el documento sigue en la base
        db.publications.update_one({"_id": ObjectId(pid)},
                                   {"$set": {"expiresAt": datetime.now(timezone.utc) - timedelta(minutes=1)}})
        assert b.get("/api/feed").json()["items"] == []
        assert b.get(f"/api/publicaciones/{pid}").status_code == 410
        assert b.put(f"/api/publicaciones/{pid}/reaccion", json={"tipo": "ME_GUSTA"}).status_code == 410
        assert db.publications.count_documents({"_id": ObjectId(pid)}) == 1
