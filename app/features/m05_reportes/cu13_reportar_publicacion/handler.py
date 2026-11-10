"""CU-13 — Reportar una publicación. Caso de uso (handler).

RF: RF-REP-01, RF-REP-03–08, RF-REP-10, RF-REP-12–15
Publicación activa de otro autor; un solo reporte por usuario y publicación. Conserva una copia
(ContenidoReportado: tipo, título, descripción y fechas) durante el plazo de conservación configurado
(inicial 7 días, RF-CFG-06). La publicación sigue su ciclo normal (RF-REP-10).
SRS v2.0, cambio 3.3: sus imágenes se copian al área de retención igual que las del chat (CU-14), así la
limpieza de la publicación no borra la evidencia; EA-05 las elimina al vencer el plazo.
"""
from datetime import timedelta

from app.shared.domain.contracts import (IClock, IConfigurationProvider, ImageStorage, IPublicationRepository,
                                        IReportRepository)
from app.shared.domain.entities import ClaveParametro, ContenidoReportado, Reporte, TipoObjetoReportado
from app.shared.domain.errors import Conflicto, NoDisponible, Prohibido

from .request import ReporteRequest, ReporteResponse

MSG_REGISTRADO = "Reporte registrado. Gracias por avisar"     # RF-REP-14
MSG_DUPLICADO = "Ya reportaste esta publicación"              # RF-REP-12
MSG_NO_DISPONIBLE = "Esta publicación ya no está disponible"


class ReportarPublicacionHandler:
    def __init__(self, publicaciones: IPublicationRepository, reportes: IReportRepository,
                 config: IConfigurationProvider, clock: IClock, imagenes: ImageStorage | None = None) -> None:
        self._imagenes = imagenes
        self._publicaciones = publicaciones
        self._reportes = reportes
        self._config = config
        self._clock = clock

    async def handle(self, estudiante_id: str, publicacion_id: str, body: ReporteRequest) -> ReporteResponse:
        ahora = self._clock.ahora()
        p = await self._publicaciones.buscar_por_id(publicacion_id)
        if p is None or not p.activa(ahora):
            raise NoDisponible(MSG_NO_DISPONIBLE, codigo="publicacion_no_disponible")
        if p.autor_id == estudiante_id:
            raise Prohibido("No puedes reportar tu propia publicación", codigo="publicacion_propia")  # RF-REP-13
        if await self._reportes.existe_reporte(estudiante_id, TipoObjetoReportado.PUBLICATION, p.id):
            raise Conflicto(MSG_DUPLICADO, codigo="reporte_duplicado")

        dias = self._config.entero(ClaveParametro.DIAS_RETENCION_REPORTES)  # RF-CFG-10: fijo al reportar
        copias: list[str] = []
        try:
            for imagen in p.imagenes:
                copias.append(await self._imagenes.copiar_a_retencion(imagen.referencia))
            await self._reportes.crear(Reporte(
                id="", reportante_id=estudiante_id, tipo_objeto=TipoObjetoReportado.PUBLICATION, objeto_id=p.id,
                codigo_motivo=body.codigo_motivo, fecha_reporte=ahora,
                fecha_retencion_fin=ahora + timedelta(days=dias), observacion=body.observacion,
                contenido=ContenidoReportado(
                    usuario_reportado_id=p.autor_id,
                    datos_publicacion={  # RF-REP-06 (publicationData)
                        "publicationId": p.id, "type": p.tipo.value, "title": p.titulo, "description": p.descripcion,
                        "authorNickname": p.nickname_autor, "createdAt": p.fecha_creacion,
                        "expiresAt": p.fecha_expiracion, "imageKeys": list(copias),
                    },
                    snapshot_imagenes=copias,
                    capturado_en=ahora,
                ),
            ))
        except Exception:
            for copia in copias:  # sin evidencia huérfana si el reporte no se registra (RNF-FIA-03)
                await self._imagenes.eliminar(copia)
            raise
        return ReporteResponse(mensaje=MSG_REGISTRADO)
