"""CU-07 — Cerrar publicación manualmente. Caso de uso (handler).

RF: RF-PUB-08, RF-PUB-11, RF-CHT-17
Solo el autor puede cerrar una publicación activa propia. No hay reapertura ni extensión (RF-PUB-11).
Los chats ya originados continúan su ciclo de vida independiente (RF-CHT-17): no se tocan.
"""
from app.shared.domain.contracts import IClock, IPublicationRepository
from app.shared.domain.errors import NoDisponible, NoEncontrado, Prohibido

MSG_NO_DISPONIBLE = "Esta publicación ya no está disponible"


class CerrarPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._clock = clock

    async def handle(self, estudiante_id: str, publicacion_id: str) -> None:
        ahora = self._clock.ahora()
        publicacion = await self._publicaciones.buscar_por_id(publicacion_id)
        if publicacion is None:
            raise NoEncontrado("La publicación no existe", codigo="publicacion_inexistente")
        if publicacion.autor_id != estudiante_id:
            raise Prohibido("Solo el autor puede cerrar esta publicación", codigo="no_es_autor")
        if not publicacion.activa(ahora) or not await self._publicaciones.cerrar(publicacion_id, estudiante_id, ahora):
            raise NoDisponible(MSG_NO_DISPONIBLE, codigo="publicacion_no_disponible")
