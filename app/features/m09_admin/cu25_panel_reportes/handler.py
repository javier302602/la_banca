"""CU-25 — Panel de reportes. Caso de uso (handler).

Muestra a los administradores TODOS los reportes juntos, más recientes primero: publicaciones y chats (de una
persona o del filtro automático) y videollamadas (quién reportó, a quién, motivo y fecha; sin video). El número
de pendientes alimenta el aviso del menú.
"""
from app.shared.domain.contracts import IAdminRepository, ImageStorage
from app.shared.domain.entities import EstadoReporte, ReporteAdmin
from app.shared.domain.errors import NoEncontrado
from app.shared.storage.image_storage import mime_de_referencia

from .request import PanelResponse, PendientesResponse, PerfilBreve, ReporteAdminResponse

LIMITE = 200


def url_imagen_retenida(r: ReporteAdmin, indice: int) -> str:
    return f"/api/admin/reportes/{r.origen}/{r.id}/imagenes/{indice}"


def respuesta(r: ReporteAdmin, perfiles: dict[str, dict]) -> ReporteAdminResponse:
    def perfil(i: str | None) -> PerfilBreve | None:
        return PerfilBreve(id=i, **perfiles[i]) if i and i in perfiles else None

    return ReporteAdminResponse(
        origen=r.origen, id=r.id, tipo=r.tipo, motivo=r.motivo, detalle=r.detalle, fecha=r.fecha, estado=r.estado.value,
        automatico=r.automatico, reportante=perfil(r.reportante_id), reportado=perfil(r.reportado_id),
        objeto_id=r.objeto_id, contenido=r.contenido,
        imagenes=[url_imagen_retenida(r, i) for i in range(len(r.imagenes))],
        archivos={clave: url_imagen_retenida(r, i) for i, clave in enumerate(r.imagenes)}, acciones=r.acciones)


class PanelReportesHandler:
    def __init__(self, admin: IAdminRepository, imagenes: ImageStorage | None = None) -> None:
        self._admin = admin
        self._imagenes = imagenes

    async def listar(self, estado: EstadoReporte | None) -> PanelResponse:
        reportes = await self._admin.listar_reportes(estado, LIMITE)
        perfiles = await self._admin.perfiles({i for r in reportes for i in (r.reportante_id, r.reportado_id) if i})
        return PanelResponse(pendientes=await self._admin.contar_pendientes(),
                             reportes=[respuesta(r, perfiles) for r in reportes])

    async def pendientes(self) -> PendientesResponse:
        return PendientesResponse(pendientes=await self._admin.contar_pendientes())

    async def imagen(self, origen: str, reporte_id: str, indice: int) -> tuple[bytes, str]:
        """Imagen o archivo retenido al reportar (el original pudo borrarse al expirar el chat)."""
        r = await self._admin.buscar_reporte(origen, reporte_id)
        clave = r.imagenes[indice] if r and 0 <= indice < len(r.imagenes) else None
        contenido = await self._imagenes.leer(clave) if clave else None
        if contenido is None:
            raise NoEncontrado("La imagen no existe", codigo="imagen_inexistente")
        return contenido, mime_de_referencia(clave)
