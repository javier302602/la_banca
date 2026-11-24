"""CU-21 — Reaccionar a una publicación. Caso de uso (handler).

Flujo: el estudiante elige una reacción → se guarda (reemplaza la anterior) o se quita si envía tipo=None.
Solo se puede reaccionar mientras la publicación está activa (no vencida ni cerrada).
"""
from app.shared.domain.contracts import IClock, IPublicationRepository, IReactionRepository
from app.shared.domain.errors import NoDisponible

from .request import ReaccionarRequest, ReaccionesResponse

MSG_NO_DISPONIBLE = "Esta publicación ya no está disponible"


class ReaccionarPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, reacciones: IReactionRepository, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._reacciones = reacciones
        self._clock = clock

    async def handle(self, estudiante_id: str, publicacion_id: str, body: ReaccionarRequest) -> ReaccionesResponse:
        ahora = self._clock.ahora()
        p = await self._publicaciones.buscar_por_id(publicacion_id)
        if p is None or not p.activa(ahora):
            raise NoDisponible(MSG_NO_DISPONIBLE, codigo="publicacion_no_disponible")
        if body.tipo is None:
            await self._reacciones.quitar(p.id, estudiante_id)
        else:
            await self._reacciones.guardar(p.id, estudiante_id, body.tipo, p.fecha_expiracion, ahora)
        resumen = await self._reacciones.resumen([p.id], estudiante_id)
        return ReaccionesResponse.desde(resumen.get(p.id))
