"""CU-24 — Reportar a la persona de una videollamada. Caso de uso (handler).

El servidor decide a quién se reporta: la otra persona de la sala. Solo puede reportar quien participó en esa
sala, así nadie reporta a un tercero inventando la sala. El reporte queda PENDIENTE para el panel de
administradores (Fase 5). No hay grabación: el reporte guarda motivo, detalle, quién, a quién y cuándo.
"""
from app.shared.domain.contracts import IClock, IVideollamadaRepository
from app.shared.domain.entities import ReporteVideollamada
from app.shared.domain.errors import NoEncontrado
from app.shared.notificaciones import avisar_a_admins

from .request import ReportarVideollamadaRequest, ReporteVideollamadaResponse

MSG_ENVIADO = "Reporte enviado. Gracias: el equipo de administradores lo revisará"


class ReportarVideollamadaHandler:
    def __init__(self, llamadas: IVideollamadaRepository, clock: IClock, avisos=None) -> None:
        self._avisos = avisos  # Fase 5: correo para avisar a los administradores
        self._llamadas = llamadas
        self._clock = clock

    async def handle(self, estudiante_id: str, body: ReportarVideollamadaRequest) -> ReporteVideollamadaResponse:
        sala = await self._llamadas.buscar_sala(body.sala_id)
        if sala is None or estudiante_id not in sala.participantes:
            raise NoEncontrado("La videollamada no existe", codigo="sala_inexistente")
        reportado = next(p for p in sala.participantes if p != estudiante_id)
        reporte_id = await self._llamadas.guardar_reporte(ReporteVideollamada(
            id="", sala_id=sala.id, reportante_id=estudiante_id, reportado_id=reportado, motivo=body.motivo,
            detalle=body.detalle, fecha=self._clock.ahora()))
        await avisar_a_admins(self._avisos, f"Nuevo reporte de una videollamada, motivo {body.motivo.value}.")
        return ReporteVideollamadaResponse(id=reporte_id, mensaje=MSG_ENVIADO)
