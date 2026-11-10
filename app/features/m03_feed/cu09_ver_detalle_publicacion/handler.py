"""CU-09 — Ver detalle de una publicación. Caso de uso (handler).

RF: RF-CHT-04, RF-FED-05, RF-FED-07, RF-FED-10, RF-FED-12
EA-02 también aplica: una publicación vencida o cerrada responde «Esta publicación ya no está disponible»
sin mostrar su contenido. En las propias no se ofrecen Responder ni Reportar; si el usuario ya tiene un
chat activo sobre la publicación, se ofrece abrirlo en lugar de responder.
"""
from app.features.m02_publicaciones.cu05_crear_publicacion.handler import url_imagen_publicacion
from app.shared.domain.contracts import IAccountRepository, IChatRepository, IClock, ImageStorage, IPublicationRepository
from app.shared.domain.errors import NoDisponible, NoEncontrado
from app.shared.domain.perfiles import apariencias
from app.shared.domain.reglas import segundos_restantes

from .request import DetallePublicacionResponse, ImagenDescargada

MSG_NO_DISPONIBLE = "Esta publicación ya no está disponible"  # RF-FED-10


class VerDetallePublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, chats: IChatRepository, clock: IClock,
                 cuentas: IAccountRepository | None = None, imagenes: ImageStorage | None = None) -> None:
        self._publicaciones = publicaciones
        self._chats = chats
        self._clock = clock
        self._cuentas = cuentas
        self._imagenes = imagenes

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
            imagenes=[url_imagen_publicacion(p.id, i) for i in range(len(p.imagenes))],
        )

    async def imagen(self, publicacion_id: str, indice: int) -> ImagenDescargada:
        """Imagen de la galería: solo mientras la publicación está activa (EA-02), con sesión iniciada."""
        p = await self._publicaciones.buscar_por_id(publicacion_id)
        if p is None or not p.activa(self._clock.ahora()):
            raise NoDisponible(MSG_NO_DISPONIBLE, codigo="publicacion_no_disponible")
        adjunta = p.imagenes[indice] if 0 <= indice < len(p.imagenes) else None
        contenido = await self._imagenes.leer(adjunta.referencia) if adjunta else None
        if contenido is None:
            raise NoEncontrado("La imagen no existe", codigo="imagen_inexistente")
        return ImagenDescargada(contenido, adjunta.mime_type)
