"""Chat v2 contra MongoDB real (SRS v2.0, Fase 4): stickers, documentos, visto, reporte y EA-03."""
from datetime import datetime, timedelta, timezone

import pytest

from app.shared.storage.image_storage import get_image_storage
from tests.e2e.test_flujo_completo import cliente, cron, registrar_y_activar

PDF = b"%PDF-1.4\n%%EOF\n"


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def test_documentos_stickers_visto_reporte_y_limpieza(db, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cr3t")
    almacen = get_image_storage()
    with cliente() as a, cliente() as b, cliente() as x:
        registrar_y_activar(a, "chat2_a@unas.edu.pe", "chat2_a")
        registrar_y_activar(b, "chat2_b@unas.edu.pe", "chat2_b")
        registrar_y_activar(x, "chat2_x@unas.edu.pe", "chat2_x")
        pid = a.post("/api/publicaciones", json={"tipo": "OFREZCO", "titulo": "Guía", "descripcion": "PDF"}).json()["id"]
        chat = b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "Hola"}).json()["chat_id"]

        r = a.post(f"/api/chats/{chat}/mensajes", data={"sticker": "sticker-15"})
        assert r.status_code == 201 and r.json()["sticker"] == "sticker-15"
        assert a.post(f"/api/chats/{chat}/mensajes", data={"sticker": "../../x"}).status_code == 422
        r = a.post(f"/api/chats/{chat}/mensajes", files={"documento": ("guia.pdf", PDF, "application/pdf")})
        assert r.status_code == 201, r.text
        doc = r.json()["documento"]
        assert doc["nombre"] == "guia.pdf" and doc["tipo"] == "pdf" and doc["tamano_bytes"] == len(PDF)
        guardado = db.messages.find_one({"documentAttachment": {"$ne": None}})["documentAttachment"]
        assert guardado["objectKey"].startswith("documentos/") and guardado["kind"] == "pdf"
        assert guardado["fileName"] == "guia.pdf" and guardado["mimeType"] == "application/pdf"
        assert db.messages.find_one({"sticker": "sticker-15"})["text"] is None

        # Solo los dos participantes descargan; siempre como adjunto y con nosniff
        r = b.get(doc["url"])
        assert r.status_code == 200 and r.content == PDF and r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["content-disposition"].startswith("attachment;")
        assert x.get(doc["url"]).status_code == 404

        # Visto: b aún no abrió → visto_hasta < último mensaje de a; tras abrir, ≥
        ultimo = db.messages.find_one({"documentAttachment": {"$ne": None}})["sentAt"].replace(tzinfo=timezone.utc)
        visto = a.get(f"/api/chats/{chat}").json()["visto_hasta"]
        assert datetime.fromisoformat(visto) < ultimo
        b.get(f"/api/chats/{chat}")
        assert datetime.fromisoformat(a.get(f"/api/chats/{chat}").json()["visto_hasta"]) >= ultimo

        # Reporte: el documento se copia a retención; EA-03 borra el original, no la copia
        assert b.post(f"/api/chats/{chat}/reportes", json={"codigo_motivo": "SPAM"}).status_code == 201
        snap = db.reports.find_one({"targetType": "CHAT"})["reportedContentSnapshot"]
        copia = next(m["document"] for m in snap["messagesSnapshot"] if m.get("document"))
        assert copia["key"].startswith("reports/") and copia["key"] in snap["retainedImageKeys"]
        assert any(m.get("sticker") == "sticker-15" for m in snap["messagesSnapshot"])
        db.chats.update_one({"_id": db.chats.find_one()["_id"]},
                            {"$set": {"expiresAt": datetime.now(timezone.utc) - timedelta(minutes=1)}})
        r = a.get("/jobs/ea03-limpiar-chats-expirados", headers=cron)
        assert r.status_code == 200 and r.json()["chats_eliminados"] == 1
        assert guardado["objectKey"] not in almacen.objetos and copia["key"] in almacen.objetos
