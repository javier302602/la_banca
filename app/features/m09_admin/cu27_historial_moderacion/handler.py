"""CU-27 — Historial de moderación. Caso de uso (handler).

Lista las últimas acciones de los administradores (quién, qué, sobre quién, cuándo y en qué reporte), con los
nicknames resueltos. Nada se borra del historial desde la app.
"""
from app.shared.domain.contracts import IAdminRepository

from .request import AccionHistorial, HistorialResponse

LIMITE = 300


class HistorialHandler:
    def __init__(self, admin: IAdminRepository) -> None:
        self._admin = admin

    async def handle(self) -> HistorialResponse:
        acciones = await self._admin.historial(LIMITE)
        perfiles = await self._admin.perfiles({a.get(c) for a in acciones for c in ("adminId", "userId") if a.get(c)})

        def nick(estudiante_id: str | None) -> str:
            return perfiles.get(estudiante_id, {}).get("nickname", "—") if estudiante_id else "—"

        return HistorialResponse(acciones=[
            AccionHistorial(fecha=a["at"], accion=a["action"], admin=nick(a.get("adminId")), usuario=nick(a.get("userId")),
                            tipo_reporte=a.get("reportType", ""), detalle=a.get("detail") or "")
            for a in acciones])
