"""CU-05 — Crear publicación. Caso de uso (handler).

RF: RF-PUB-01–07, RF-PUB-12–16 · SRS v2.0, cambio 3.1
Duración fija de 24 h (DURACION_PUBLICACION, RN-09): no se elige ni se acepta desde la solicitud.
Máximo de publicaciones activas por autor desde CFG (valor inicial 3, RF-CFG-03), verificado al confirmar
de forma atómica: dos creaciones simultáneas del mismo autor no pueden superar el máximo.

Hasta 3 imágenes con las mismas reglas que las del chat: JPG/PNG/WebP ≤ 5 MB detectados por el contenido,
decodificadas y vueltas a codificar sin EXIF. Se guardan antes de crear la publicación y se borran si la
creación falla (por ejemplo, sin cupo), para no dejar objetos huérfanos.
"""
from app.shared.domain.contracts import IClock, IConfigurationProvider, ImageStorage, IPublicationRepository
from app.shared.domain.entities import (DURACION_PUBLICACION, MAX_IMAGENES_PUBLICACION, ClaveParametro, ImagenAdjunta,
                                        Publicacion)
from app.shared.domain.errors import Conflicto, ErrorValidacion
from app.shared.domain.reglas import segundos_restantes, validar_imagen

PREFIJO_IMAGENES = "publicaciones"
MSG_DEMASIADAS = f"Puedes adjuntar hasta {MAX_IMAGENES_PUBLICACION} imágenes"


def url_imagen_publicacion(publicacion_id: str, indice: int) -> str:
    return f"/api/publicaciones/{publicacion_id}/imagenes/{indice}"

from .request import CrearPublicacionRequest, CupoResponse, PublicacionResponse


class CrearPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, config: IConfigurationProvider, clock: IClock,
                 imagenes: ImageStorage | None = None) -> None:
        self._publicaciones = publicaciones
        self._config = config
        self._clock = clock
        self._imagenes = imagenes

    async def handle(self, estudiante_id: str, nickname: str, body: CrearPublicacionRequest,
                     imagenes: list[bytes] | None = None) -> PublicacionResponse:
        ahora = self._clock.ahora()
        maximo = self._config.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS)
        formatos = self._validar_imagenes(imagenes or [])
        if formatos and await self._publicaciones.contar_activas_por_usuario(estudiante_id, ahora) >= maximo:
            raise self._sin_cupo(maximo)  # antes de procesar imágenes que no se usarían
        adjuntas = await self._guardar(imagenes or [], formatos)
        publicacion = Publicacion(
            id="", autor_id=estudiante_id, nickname_autor=nickname, tipo=body.tipo, titulo=body.titulo,
            descripcion=body.descripcion, fecha_creacion=ahora,
            fecha_expiracion=ahora + DURACION_PUBLICACION,  # RF-PUB-05 / RF-PUB-07
            imagenes=adjuntas,
        )
        try:
            publicacion_id = await self._publicaciones.crear_si_hay_cupo(publicacion, maximo, ahora)
        except Exception:
            await self._borrar(adjuntas)
            raise
        if publicacion_id is None:
            await self._borrar(adjuntas)
            raise self._sin_cupo(maximo)
        publicacion.id = publicacion_id
        return PublicacionResponse(
            id=publicacion.id, tipo=publicacion.tipo, titulo=publicacion.titulo,
            descripcion=publicacion.descripcion, nickname_autor=nickname, fecha_creacion=ahora,
            fecha_expiracion=publicacion.fecha_expiracion,
            segundos_restantes=segundos_restantes(publicacion.fecha_expiracion, ahora),
            imagenes=[url_imagen_publicacion(publicacion.id, i) for i in range(len(adjuntas))],
        )

    @staticmethod
    def _sin_cupo(maximo: int) -> Conflicto:
        return Conflicto(f"Ya tienes {maximo} publicaciones activas. Cierra una o espera a que expire",  # RF-PUB-06
                         codigo="limite_publicaciones")

    @staticmethod
    def _validar_imagenes(imagenes: list[bytes]) -> list[str]:
        if len(imagenes) > MAX_IMAGENES_PUBLICACION:
            raise ErrorValidacion(MSG_DEMASIADAS, codigo="demasiadas_imagenes", campo="imagenes")
        formatos = []
        for contenido in imagenes:
            try:
                formatos.append(validar_imagen(contenido))
            except ValueError as e:
                raise ErrorValidacion(str(e), codigo="imagen_invalida", campo="imagenes") from None
        return formatos

    async def _guardar(self, imagenes: list[bytes], formatos: list[str]) -> list[ImagenAdjunta]:
        adjuntas: list[ImagenAdjunta] = []
        try:
            for contenido, mime in zip(imagenes, formatos):
                referencia = await self._imagenes.guardar(contenido, mime, PREFIJO_IMAGENES)
                adjuntas.append(ImagenAdjunta(referencia, mime, len(contenido), self._imagenes.bucket))
        except ErrorValidacion as e:
            await self._borrar(adjuntas)
            raise ErrorValidacion(e.mensaje, codigo="imagen_invalida", campo="imagenes") from None
        except Exception:
            await self._borrar(adjuntas)
            raise
        return adjuntas

    async def _borrar(self, adjuntas: list[ImagenAdjunta]) -> None:
        for a in adjuntas:
            await self._imagenes.eliminar(a.referencia)

    async def cupo(self, estudiante_id: str) -> CupoResponse:
        activas = await self._publicaciones.contar_activas_por_usuario(estudiante_id, self._clock.ahora())
        return CupoResponse(activas=activas, maximo=self._config.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS))
