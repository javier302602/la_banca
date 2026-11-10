"""CU-08 — Consultar el feed «Ahora». Caso de uso (handler).

RF: RF-FED-01–04, RF-FED-06–09, RF-FED-11–13, RF-FED-15–19
EA-02 (Expirar publicación; RF-PUB-09, RF-FED-02) se evalúa en la consulta: solo entran publicaciones con
estado ACTIVE y fecha_expiracion > ahora. Filtro opcional por tipo (RN-44), orden por creación descendente
(RF-FED-03) y bloques de 20 con cursor (RF-FED-19). Las propias se marcan «Tu publicación» (RF-FED-07).
"""
from app.features.m02_publicaciones.cu05_crear_publicacion.handler import url_imagen_publicacion
from app.shared.domain.contracts import IAccountRepository, IClock, IPublicationRepository
from app.shared.domain.entities import TAMANO_BLOQUE_FEED
from app.shared.domain.perfiles import apariencias
from app.shared.domain.reglas import segundos_restantes

from .request import ConsultarFeedRequest, FeedItemResponse, FeedResponse

MSG_VACIO = "No hay publicaciones activas en este momento"               # RF-FED-06
MSG_VACIO_TIPO = "No hay publicaciones de este tipo en este momento"     # RF-FED-15


class ConsultarFeedHandler:
    def __init__(self, publicaciones: IPublicationRepository, clock: IClock,
                 cuentas: IAccountRepository | None = None) -> None:
        self._publicaciones = publicaciones
        self._clock = clock
        self._cuentas = cuentas

    async def handle(self, estudiante_id: str, body: ConsultarFeedRequest) -> FeedResponse:
        ahora = self._clock.ahora()
        bloque, siguiente = await self._publicaciones.listar_feed(ahora, body.tipo, body.cursor, TAMANO_BLOQUE_FEED)
        bloque = [p for p in bloque if p.activa(ahora)]
        caras = await apariencias(self._cuentas, {p.autor_id: p.nickname_autor for p in bloque})
        items = [
            FeedItemResponse(id=p.id, tipo=p.tipo, titulo=p.titulo, nickname_autor=p.nickname_autor,
                             apariencia_autor=caras[p.autor_id],
                             fecha_creacion=p.fecha_creacion, fecha_expiracion=p.fecha_expiracion,
                             segundos_restantes=segundos_restantes(p.fecha_expiracion, ahora),
                             es_propia=p.autor_id == estudiante_id, num_imagenes=len(p.imagenes),
                             miniatura=url_imagen_publicacion(p.id, 0) if p.imagenes else None)
            for p in bloque
        ]
        vacio = None
        if not items and body.cursor is None:
            vacio = MSG_VACIO_TIPO if body.tipo else MSG_VACIO
        return FeedResponse(ahora=ahora, items=items, siguiente_cursor=siguiente, mensaje_vacio=vacio)
