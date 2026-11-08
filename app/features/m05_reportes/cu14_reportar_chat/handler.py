"""CU-14 — Reportar un chat. Caso de uso (handler).

RF: RF-REP-02–05, RF-REP-07, RF-REP-08, RF-REP-10, RF-REP-14–17
Solo un participante de un chat activo. La instantánea (ContenidoReportado) copia todos los mensajes de
texto y todas las imágenes existentes en ese momento (RF-REP-17); cada imagen se copia al área de
retención con ImageStorage.copiar_a_retencion, de modo que la limpieza del chat (EA-03) no la afecte.
Se permiten reportes sucesivos del mismo chat, cada uno con su propio plazo (RF-REP-16).
"""
from datetime import timedelta

from app.shared.domain.contracts import IChatRepository, IClock, IConfigurationProvider, ImageStorage, IReportRepository
from app.shared.domain.entities import ClaveParametro, ContenidoReportado, Reporte, TipoObjetoReportado
from app.shared.domain.errors import NoDisponible, NoEncontrado

from .request import ReporteRequest, ReporteResponse

MSG_REGISTRADO = "Reporte registrado. Gracias por avisar"  # RF-REP-14


class ReportarChatHandler:
    def __init__(self, chats: IChatRepository, reportes: IReportRepository, imagenes: ImageStorage,
                 config: IConfigurationProvider, clock: IClock) -> None:
        self._chats = chats
        self._reportes = reportes
        self._imagenes = imagenes
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str, chat_id: str, body: ReporteRequest) -> ReporteResponse:
        ahora = self._clock.ahora()
        chat = await self._chats.buscar_por_id(chat_id)
        if chat is None or estudiante_id not in chat.participantes:
            raise NoEncontrado("El chat no existe", codigo="chat_inexistente")  # RF-REP-02 / RNF-SEG-04
        if not chat.activo(ahora):
            raise NoDisponible("Este chat expiró", codigo="chat_expirado")

        copias: list[str] = []
        try:
            snapshot_mensajes = []
            for m in await self._chats.listar_mensajes(chat.id):
                retenida = None
                if m.imagen is not None:
                    retenida = await self._imagenes.copiar_a_retencion(m.imagen.referencia)
                    copias.append(retenida)
                snapshot_mensajes.append({"messageId": m.id, "senderId": m.emisor_id,  # Entregable 2 §5.3
                                          "senderNickname": m.nickname_emisor, "text": m.texto,
                                          "imageKey": retenida, "sentAt": m.fecha_envio})
            dias = self._config.entero(ClaveParametro.DIAS_RETENCION_REPORTES)
            await self._reportes.crear(Reporte(
                id="", reportante_id=estudiante_id, tipo_objeto=TipoObjetoReportado.CHAT, objeto_id=chat.id,
                codigo_motivo=body.codigo_motivo, fecha_reporte=ahora,
                fecha_retencion_fin=ahora + timedelta(days=dias), observacion=body.observacion,
                contenido=ContenidoReportado(
                    usuario_reportado_id=chat.contraparte(estudiante_id)[0],  # RF-REP-07
                    mensajes=snapshot_mensajes,  # RF-REP-17
                    snapshot_imagenes=copias,
                    datos_publicacion={"publicationId": chat.publicacion_id,  # contexto de la publicación de origen
                                       "type": chat.tipo_publicacion.value, "title": chat.titulo_publicacion},
                    capturado_en=ahora,
                ),
            ))
        except Exception:
            for copia in copias:  # sin evidencia huérfana si el reporte no se registra (RNF-FIA-03)
                await self._imagenes.eliminar(copia)
            raise
        return ReporteResponse(mensaje=MSG_REGISTRADO)
