"""CU-26 — Moderar un reporte. Caso de uso (handler).

Acciones del administrador sobre un reporte:
- ELIMINAR_CONTENIDO: la publicación queda oculta (REMOVED) o el chat se borra con sus archivos. Una
  videollamada no tiene contenido guardado: ahí solo caben acciones sobre la cuenta.
- ADVERTIR: la persona ve el aviso la próxima vez que entra (y lo recibe por correo).
- SUSPENDER (1–365 días) o BANEAR: se cierran sus sesiones y no puede volver a entrar mientras dure.
- DESCARTAR: el reporte no procede.
Cada acción queda en el historial (admin_actions) y en el propio reporte, que pasa a RESUELTO o DESCARTADO.
Nadie puede sancionar a un administrador ni a sí mismo.
"""
import logging
from datetime import timedelta

from app.shared.clock import formato_fecha_hora
from app.shared.config.moderacion import es_admin
from app.shared.domain.contracts import IAdminRepository, IClock, IEmailSender, ImageStorage
from app.shared.domain.entities import AccionAdmin, EstadoReporte, ReporteAdmin
from app.shared.domain.errors import ErrorValidacion, NoEncontrado, Prohibido

from .request import AccionRequest

log = logging.getLogger("la_banca.cu26")

AVISO_POR_OMISION = "Un administrador revisó un reporte sobre tu contenido. Respeta las normas de convivencia de La Banca."
SOBRE_LA_CUENTA = {AccionAdmin.ADVERTIR, AccionAdmin.SUSPENDER, AccionAdmin.BANEAR}


class ModerarReporteHandler:
    def __init__(self, admin: IAdminRepository, imagenes: ImageStorage, correo: IEmailSender, clock: IClock) -> None:
        self._admin = admin
        self._imagenes = imagenes
        self._correo = correo
        self._clock = clock

    async def handle(self, admin_id: str, origen: str, reporte_id: str, body: AccionRequest) -> ReporteAdmin:
        ahora = self._clock.ahora()
        reporte = await self._admin.buscar_reporte(origen, reporte_id)
        if reporte is None:
            raise NoEncontrado("El reporte no existe", codigo="reporte_inexistente")

        detalle = ""
        if body.accion is AccionAdmin.ELIMINAR_CONTENIDO:
            detalle = await self._eliminar_contenido(reporte)
        elif body.accion in SOBRE_LA_CUENTA:
            detalle = await self._sancionar(admin_id, reporte, body)

        estado = EstadoReporte.DESCARTADO if body.accion is AccionAdmin.DESCARTAR else EstadoReporte.RESUELTO
        accion = {"action": body.accion.value, "adminId": admin_id, "at": ahora, "detail": detalle}
        await self._admin.marcar_reporte(origen, reporte_id, estado, accion)
        await self._admin.registrar_accion({**accion, "reportOrigin": origen, "reportId": reporte_id,
                                            "reportType": reporte.tipo, "userId": reporte.reportado_id})
        return await self._admin.buscar_reporte(origen, reporte_id)

    async def _eliminar_contenido(self, reporte: ReporteAdmin) -> str:
        if reporte.tipo == "PUBLICACION":
            await self._admin.eliminar_publicacion(reporte.objeto_id, self._clock.ahora())
            return "Publicación ocultada"
        if reporte.tipo == "CHAT":
            for clave in await self._admin.eliminar_chat(reporte.objeto_id):
                try:
                    await self._imagenes.eliminar(clave)
                except Exception:  # queda huérfano en el almacenamiento; no impide la moderación
                    log.exception("No se pudo borrar un archivo del chat eliminado")
            return "Chat eliminado"
        raise ErrorValidacion("Una videollamada no guarda contenido: usa advertir, suspender o banear",
                              codigo="sin_contenido")

    async def _sancionar(self, admin_id: str, reporte: ReporteAdmin, body: AccionRequest) -> str:
        cuenta = await self._admin.buscar_cuenta(reporte.reportado_id) if reporte.reportado_id else None
        if cuenta is None:
            raise NoEncontrado("La cuenta reportada ya no existe", codigo="cuenta_inexistente")
        if cuenta.id == admin_id or es_admin(cuenta.correo_institucional):
            raise Prohibido("No se puede sancionar a un administrador", codigo="sancion_a_admin")
        ahora = self._clock.ahora()
        if body.accion is AccionAdmin.ADVERTIR:
            texto = body.mensaje or AVISO_POR_OMISION
            await self._admin.advertir(cuenta.id, texto)
            await self._avisar(cuenta.correo_institucional, "Advertencia de La Banca", texto)
            return f"Advertencia: {texto}"
        if body.accion is AccionAdmin.SUSPENDER:
            hasta = ahora + timedelta(days=body.dias)
            await self._admin.suspender(cuenta.id, hasta, ahora)
            await self._avisar(cuenta.correo_institucional, "Tu cuenta de La Banca fue suspendida",
                               f"Tu cuenta está suspendida hasta el {formato_fecha_hora(hasta)} por un reporte revisado "
                               "por el equipo de administradores.")
            return f"Suspendida {body.dias} día(s), hasta {formato_fecha_hora(hasta)}"
        await self._admin.banear(cuenta.id, ahora)
        await self._avisar(cuenta.correo_institucional, "Tu cuenta de La Banca fue bloqueada",
                           "Tu cuenta fue bloqueada por incumplir las normas de La Banca.")
        return "Cuenta bloqueada"

    async def _avisar(self, correo: str, asunto: str, cuerpo: str) -> None:
        try:
            await self._correo.enviar_aviso(correo, asunto, cuerpo)
        except Exception:  # el aviso por correo no impide la sanción
            log.exception("No se pudo enviar el aviso de moderación")
