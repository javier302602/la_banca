"""CU-23 — Videollamada. Implementación Mongo (funciona con varios workers de gunicorn).

Colecciones (todas vencen solas con índices TTL, ver app/shared/db/mongo.py):
- videocall_queue:   {userId, nickname, fullName, career, avoid: [userId], expiresAt}  quien espera pareja.
- videocall_rooms:   {participants: [a, b], startedAt, endedAt, expiresAt}             quién habló con quién.
- videocall_signals: {to, message, expiresAt}                                          buzón por estudiante.

Emparejar es atómico: `find_one_and_delete` saca de la cola a una sola persona, así dos workers nunca toman a
la misma. El azar sale de `$sample` (se prueban hasta 5 candidatos por si otro worker se adelanta).
"""
from pymongo import ASCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mongo import oid
from app.shared.domain.contracts import IVideollamadaRepository
from app.shared.domain.entities import VIGENCIA_SALA, EstadoCuenta, ParticipanteVideollamada, SalaVideollamada

CANDIDATOS = 5


def _participante(doc: dict) -> ParticipanteVideollamada:
    return ParticipanteVideollamada(estudiante_id=str(doc["userId"]), nickname=doc["nickname"],
                                    nombre=doc["fullName"], carrera=doc["career"])


def _sala(doc: dict) -> SalaVideollamada:
    return SalaVideollamada(id=str(doc["_id"]), participantes=[str(p) for p in doc["participants"]],
                            inicio=doc["startedAt"], fin=doc.get("endedAt"))


class MongoVideollamadaRepository(IVideollamadaRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_participante(self, estudiante_id):
        clave = oid(estudiante_id)
        doc = await self._db.accounts.find_one({"_id": clave, "status": EstadoCuenta.ACTIVA.value},
                                               {"nickname": 1, "fullName": 1, "career": 1}) if clave else None
        if doc is None:
            return None
        return ParticipanteVideollamada(estudiante_id=str(doc["_id"]), nickname=doc["nickname"],
                                        nombre=doc.get("fullName") or "", carrera=doc.get("career") or "")

    # --- cola ---------------------------------------------------------------------------------------------
    async def entrar_a_la_cola(self, yo, evitar, expira_en):
        await self._db.videocall_queue.replace_one(
            {"userId": oid(yo.estudiante_id)},
            {"userId": oid(yo.estudiante_id), "nickname": yo.nickname, "fullName": yo.nombre, "career": yo.carrera,
             "avoid": [oid(e) for e in evitar], "expiresAt": expira_en},
            upsert=True)

    async def salir_de_la_cola(self, estudiante_id):
        return await self._db.videocall_queue.find_one_and_delete({"userId": oid(estudiante_id)}) is not None

    async def tomar_al_azar(self, yo_id, evitar, ahora):
        yo = oid(yo_id)
        filtro = {"userId": {"$nin": [yo, *(oid(e) for e in evitar)]}, "avoid": {"$ne": yo},
                  "expiresAt": {"$gt": ahora}}
        candidatos = await (await self._db.videocall_queue.aggregate(
            [{"$match": filtro}, {"$sample": {"size": CANDIDATOS}}])).to_list(CANDIDATOS)
        for candidato in candidatos:
            tomado = await self._db.videocall_queue.find_one_and_delete({"_id": candidato["_id"]})
            if tomado is not None:  # si otro worker se adelantó, se prueba el siguiente
                return _participante(tomado)
        return None

    # --- salas ---------------------------------------------------------------------------------------------
    async def crear_sala(self, participantes, ahora):
        doc = {"participants": [oid(p) for p in participantes], "startedAt": ahora, "endedAt": None,
               "expiresAt": ahora + VIGENCIA_SALA}
        resultado = await self._db.videocall_rooms.insert_one(doc)
        doc["_id"] = resultado.inserted_id
        return _sala(doc)

    async def cerrar_sala(self, sala_id, ahora):
        await self._db.videocall_rooms.update_one({"_id": oid(sala_id), "endedAt": None}, {"$set": {"endedAt": ahora}})

    async def buscar_sala(self, sala_id):
        clave = oid(sala_id)
        doc = await self._db.videocall_rooms.find_one({"_id": clave}) if clave else None
        return _sala(doc) if doc else None

    # --- buzón -----------------------------------------------------------------------------------------------
    async def enviar(self, para, mensaje, expira_en):
        await self._db.videocall_signals.insert_one({"to": oid(para), "message": mensaje, "expiresAt": expira_en})

    async def recibir(self, estudiante_id):
        docs = await (self._db.videocall_signals.find({"to": oid(estudiante_id)})
                      .sort("_id", ASCENDING).limit(50).to_list(50))
        if docs:
            await self._db.videocall_signals.delete_many({"_id": {"$in": [d["_id"] for d in docs]}})
        return [d["message"] for d in docs]
