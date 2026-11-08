"""EA-03 — Expirar chat por inactividad (limpieza física). Automatismo (handler).

RF: RF-CHT-12, RF-CHT-13, RF-CHT-15–17, RF-CHT-25 · RNF-PRI-03
El bloqueo de acceso ya se evalúa en cada consulta (Chat.activo). Este job elimina definitivamente
los chats con ultima_actividad + 24 h ≤ ahora, sus mensajes y sus imágenes. El contenido reportado no
se pierde: CU-14 lo copió al reporte y al área de retención de imágenes (RF-CHT-16).
"""
import logging

from app.shared.domain.contracts import IChatRepository, IClock, ImageStorage

log = logging.getLogger("la_banca.ea03")


class LimpiarChatsExpiradosHandler:
    def __init__(self, chats: IChatRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._chats = chats
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self) -> dict[str, int]:
        eliminados, referencias = await self._chats.eliminar_expirados(self._clock.ahora())
        borradas = 0
        for referencia in referencias:
            try:
                await self._imagenes.eliminar(referencia)
                borradas += 1
            except Exception:  # se reintenta en la próxima ejecución del almacenamiento; no detiene el job
                log.exception("No se pudo eliminar una imagen de chat expirado")
        return {"chats_eliminados": eliminados, "imagenes_eliminadas": borradas}
