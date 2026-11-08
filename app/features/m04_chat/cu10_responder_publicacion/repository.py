"""CU-10 — Responder a una publicación. Implementación Mongo de lo que necesita el slice."""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.domain.contracts import IChatRepository, IPublicationRepository


class MongoPublicacionLecturaRepository(IPublicationRepository):
    """Implementa de IPublicationRepository: buscar_por_id."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_id(self, *args, **kwargs):
        raise NotImplementedError


class MongoResponderPublicacionRepository(IChatRepository):
    """Implementa de IChatRepository: buscar_por_usuario_y_publicacion, crear_con_primer_mensaje."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def buscar_por_usuario_y_publicacion(self, *args, **kwargs):
        raise NotImplementedError

    async def crear_con_primer_mensaje(self, *args, **kwargs):
        raise NotImplementedError
