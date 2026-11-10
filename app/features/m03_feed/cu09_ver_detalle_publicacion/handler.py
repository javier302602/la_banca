"""CU-09 — Ver detalle de una publicación. Caso de uso (handler).

RF: RF-CHT-04, RF-FED-05, RF-FED-07, RF-FED-10, RF-FED-12
EA-02 también aplica: una publicación vencida o cerrada responde «Esta publicación ya no está disponible»
sin mostrar su contenido. En las propias no se ofrecen Responder ni Reportar; si el usuario ya tiene un
chat activo sobre la publicación, se ofrece abrirlo en lugar de responder.
"""
from app.shared.domain.contracts import IAccountRepository, IChatRepository, IClock, IPublicationRepository
from app.shared.domain.errors import NoDisponible
from app.shared.domain.perfiles import apariencias
from app.shared.domain.reglas import segundos_restantes

from .request import DetallePublicacionResponse

MSG_NO_DISPONIBLE = "Esta publicación ya no está disponible"  # RF-FED-10


class VerDetallePublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, chats: IChatRepository, clock: IClock,
                 cuentas: IAccountRepository | None = None) -> None:
        self._publicaciones = publicaciones
        self._chats = chats
        self._clock = clock
        self._cuentas = cuentas

    async def handle(self, estudiante_id: str, publicacion_id: str) -> DetallePublicacionResponse:
        ahora = self._clock.ahora()
        p = await self._publicaciones.buscar_por_id(publicacion_id)
        if p is None or not p.activa(ahora):
            raise NoDisponible(MSG_NO_DISPONIBLE, codigo="publicacion_no_disponible")
        es_propia = p.autor_id == estudiante_id
        chat_id = None
        if not es_propia:
            chat = await self._chats.buscar_por_usuario_y_publicacion(estudiante_id, p.id)
            chat_id = chat.id if chat and chat.activo(ahora) else None
        cara = (await apariencias(self._cuentas, {p.autor_id: p.nickname_autor}))[p.autor_id]
        return DetallePublicacionResponse(
            ahora=ahora, id=p.id, tipo=p.tipo, titulo=p.titulo, descripcion=p.descripcion,
            nickname_autor=p.nickname_autor, apariencia_autor=cara, fecha_expiracion=p.fecha_expiracion,
            segundos_restantes=segundos_restantes(p.fecha_expiracion, ahora), es_propia=es_propia,
            puede_responder=not es_propia and chat_id is None, puede_reportar=not es_propia,
            chat_existente_id=chat_id,
        )
