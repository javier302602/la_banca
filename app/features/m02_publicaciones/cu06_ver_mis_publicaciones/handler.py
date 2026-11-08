"""CU-06 — Ver mis publicaciones activas. Caso de uso (handler).

RF: RF-PUB-10, RF-FED-09
Lista solo las publicaciones vigentes del autor (EA-02 al consultar), de la más reciente a la más antigua,
con su tiempo restante calculado con la hora del sistema.
"""
from app.shared.domain.contracts import IClock, IPublicationRepository
from app.shared.domain.reglas import segundos_restantes

from .request import MiPublicacionResponse, MisPublicacionesResponse


class VerMisPublicacionesHandler:
    def __init__(self, publicaciones: IPublicationRepository, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._clock = clock

    async def handle(self, estudiante_id: str) -> MisPublicacionesResponse:
        ahora = self._clock.ahora()
        propias = await self._publicaciones.listar_activas_por_usuario(estudiante_id, ahora)
        return MisPublicacionesResponse(ahora=ahora, items=[
            MiPublicacionResponse(id=p.id, tipo=p.tipo, titulo=p.titulo, fecha_creacion=p.fecha_creacion,
                                  fecha_expiracion=p.fecha_expiracion,
                                  segundos_restantes=segundos_restantes(p.fecha_expiracion, ahora))
            for p in propias if p.activa(ahora)
        ])
