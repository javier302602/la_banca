"""EA-03 — Expirar chat por inactividad (limpieza física). Automatismo (handler).

RF: RF-CHT-12, RF-CHT-13, RF-CHT-15–17, RF-CHT-25
El bloqueo de acceso se evalúa en cada consulta; este job solo depura físicamente chats con ultima_actividad + 24 h ≤ ahora y sin retención activa por reporte (incluye imágenes).

Depende solo de los contratos de app.shared.domain.contracts (nunca de motor/pymongo).
"""
from app.shared.domain.contracts import IChatRepository, IClock, ImageStorage


class LimpiarChatsExpiradosHandler:
    def __init__(self, chats: IChatRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._chats = chats
        self._imagenes = imagenes
        self._clock = clock

    async def handle(self) -> int:
        """Ejecuta la limpieza y devuelve la cantidad depurada."""
        raise NotImplementedError
