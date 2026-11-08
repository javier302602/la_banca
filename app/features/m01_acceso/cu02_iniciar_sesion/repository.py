"""CU-02 — Iniciar sesión. Implementación Mongo de lo que necesita el slice."""
from pymongo.asynchronous.database import AsyncDatabase

from app.shared.db.mapeo import doc_a_estudiante, doc_a_intento, intento_a_doc, sesion_a_doc
from app.shared.domain.contracts import IAccountRepository


class MongoIniciarSesionRepository(IAccountRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db

    async def buscar_por_correo(self, correo):
        doc = await self._db.accounts.find_one({"email": correo})
        return doc_a_estudiante(doc) if doc else None

    async def obtener_intento(self, correo):
        doc = await self._db.login_attempts.find_one({"email": correo})
        return doc_a_intento(doc) if doc else None

    async def guardar_intento(self, intento):
        await self._db.login_attempts.replace_one({"email": intento.correo_ingresado}, intento_a_doc(intento),
                                                  upsert=True)

    async def reiniciar_intentos(self, correo):
        await self._db.login_attempts.delete_one({"email": correo})

    async def crear_sesion(self, sesion):
        resultado = await self._db.sessions.insert_one(sesion_a_doc(sesion))
        return str(resultado.inserted_id)
