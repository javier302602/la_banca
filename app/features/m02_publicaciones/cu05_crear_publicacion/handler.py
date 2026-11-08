"""CU-05 — Crear publicación. Caso de uso (handler).

RF: RF-PUB-01–07, RF-PUB-12–16
Duración fija de 24 h (DURACION_PUBLICACION, RN-09): no se elige ni se acepta desde la solicitud.
Máximo de publicaciones activas por autor desde CFG (valor inicial 3, RF-CFG-03), verificado al confirmar.
"""
from app.shared.domain.contracts import IClock, IConfigurationProvider, IPublicationRepository
from app.shared.domain.entities import DURACION_PUBLICACION, ClaveParametro, Publicacion
from app.shared.domain.errors import Conflicto
from app.shared.domain.reglas import segundos_restantes

from .request import CrearPublicacionRequest, CupoResponse, PublicacionResponse


class CrearPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, config: IConfigurationProvider, clock: IClock) -> None:
        self._publicaciones = publicaciones
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str, nickname: str, body: CrearPublicacionRequest) -> PublicacionResponse:
        ahora = self._clock.ahora()
        maximo = self._config.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS)
        if await self._publicaciones.contar_activas_por_usuario(estudiante_id, ahora) >= maximo:
            raise Conflicto(f"Ya tienes {maximo} publicaciones activas. Cierra una o espera a que expire",  # RF-PUB-06
                            codigo="limite_publicaciones")
        publicacion = Publicacion(
            id="", autor_id=estudiante_id, nickname_autor=nickname, tipo=body.tipo, titulo=body.titulo,
            descripcion=body.descripcion, fecha_creacion=ahora,
            fecha_expiracion=ahora + DURACION_PUBLICACION,  # RF-PUB-05 / RF-PUB-07
        )
        publicacion.id = await self._publicaciones.crear(publicacion)
        return PublicacionResponse(
            id=publicacion.id, tipo=publicacion.tipo, titulo=publicacion.titulo,
            descripcion=publicacion.descripcion, nickname_autor=nickname, fecha_creacion=ahora,
            fecha_expiracion=publicacion.fecha_expiracion,
            segundos_restantes=segundos_restantes(publicacion.fecha_expiracion, ahora),
        )

    async def cupo(self, estudiante_id: str) -> CupoResponse:
        activas = await self._publicaciones.contar_activas_por_usuario(estudiante_id, self._clock.ahora())
        return CupoResponse(activas=activas, maximo=self._config.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS))
