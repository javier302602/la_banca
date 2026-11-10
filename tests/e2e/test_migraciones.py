"""Migración 001 (v1 → v2) contra MongoDB real: idempotente, registrada y con un solo proceso migrando."""
import asyncio
from datetime import datetime, timezone

from bson import ObjectId

from app.shared.db import migraciones


def test_001_convierte_datos_v1_una_sola_vez(base_e2e_limpia):
    db_sync = base_e2e_limpia
    ahora = datetime.now(timezone.utc)
    cuenta, pub, chat = ObjectId(), ObjectId(), ObjectId()
    # Documentos tal como los escribía la v1.0.0 (sin los campos de la v2)
    db_sync.accounts.insert_one({"_id": cuenta, "email": "v1@unas.edu.pe", "passwordHash": "x" * 60,
                                 "nickname": "de_v1", "status": "ACTIVA", "createdAt": ahora})
    db_sync.publications.insert_one({"_id": pub, "authorId": cuenta, "authorNickname": "de_v1", "type": "OFREZCO",
                                     "title": "t", "description": "d", "createdAt": ahora, "expiresAt": ahora,
                                     "closedAt": None, "status": "ACTIVE"})
    db_sync.messages.insert_many([
        {"chatId": chat, "senderId": cuenta, "senderNickname": "de_v1", "text": "hola", "imageAttachment": None,
         "sentAt": ahora},
        {"chatId": chat, "senderId": cuenta, "senderNickname": "de_v1", "text": None, "sentAt": ahora,
         "imageAttachment": {"objectKey": "chats/a.png", "mimeType": "image/png", "sizeBytes": 9}}])
    # Una cuenta ya «v2» no se toca
    db_sync.accounts.insert_one({"_id": ObjectId(), "email": "v2@unas.edu.pe", "passwordHash": "x" * 60,
                                 "nickname": "de_v2", "status": "ACTIVA", "createdAt": ahora, "bio": "hola",
                                 "avatar": "avatar-03", "photo": None})

    async def correr():
        from app.shared.db.mongo import base_de_datos

        db = base_de_datos()
        # Tres procesos arrancando a la vez: solo uno aplica la migración
        resultados = await asyncio.gather(*(migraciones.aplicar_pendientes(db, version_app="2.0.0") for _ in range(3)))
        segunda = await migraciones.aplicar_pendientes(db, version_app="2.0.0")
        return resultados, segunda

    resultados, segunda = asyncio.run(correr())
    assert sorted(len(r) for r in resultados) == [0, 0, 1] and segunda == []
    registro = db_sync.schema_migrations.find_one({"_id": "001_v1_a_v2"})
    assert registro["versionApp"] == "2.0.0" and registro["resumen"]["accounts.bio"] == 1
    assert db_sync.schema_migrations_lock.count_documents({}) == 0  # el bloqueo se liberó

    v1 = db_sync.accounts.find_one({"_id": cuenta})
    assert v1["bio"] == "" and v1["avatar"] is None and v1["photo"] is None
    assert db_sync.accounts.find_one({"nickname": "de_v2"})["avatar"] == "avatar-03"
    assert db_sync.publications.find_one({"_id": pub})["images"] == []
    for m in db_sync.messages.find():
        assert m["sticker"] is None and m["documentAttachment"] is None
    assert db_sync.messages.count_documents({"imageAttachment.objectKey": "chats/a.png"}) == 1  # intacto

    # El código de v2 lee los documentos migrados
    from app.shared.db.mapeo import doc_a_estudiante, doc_a_mensaje, doc_a_publicacion
    assert doc_a_estudiante(v1).biografia == "" and doc_a_publicacion(db_sync.publications.find_one()).imagenes == []
    assert all(doc_a_mensaje(m).sticker is None for m in db_sync.messages.find())


def test_bloqueo_abandonado_vence(base_e2e_limpia):
    from datetime import timedelta

    base_e2e_limpia.schema_migrations.delete_many({})  # como si la 001 no se hubiera aplicado
    base_e2e_limpia.schema_migrations_lock.insert_one(
        {"_id": "migraciones", "dueno": "proceso-muerto", "venceEn": datetime.now(timezone.utc) - timedelta(minutes=1)})

    async def correr():
        from app.shared.db.mongo import base_de_datos

        return await migraciones.aplicar_pendientes(base_de_datos(), version_app="2.0.0")

    assert asyncio.run(correr()) == ["001_v1_a_v2"]
