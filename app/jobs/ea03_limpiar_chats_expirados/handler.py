"""EA-03 — Expirar chat por inactividad (limpieza física). Automatismo (handler).

RF: RF-CHT-12, RF-CHT-13, RF-CHT-15–17, RF-CHT-25 · RNF-PRI-03
El bloqueo de acceso ya se evalúa en cada consulta (Chat.activo). Este job elimina definitivamente
los chats con ultima_actividad + 24 h ≤ ahora, sus mensajes y sus imágenes. El contenido reportado no
se pierde: CU-14 lo copió al reporte y al área de retención de imágenes (RF-CHT-16).

SRS v2.0, cambio 3.4: también borra las imágenes de las publicaciones vencidas o cerradas (las de una
publicación reportada ya están copiadas en retención por CU-13).
"""
import logging

from app.shared.domain.contracts import IChatRepository, IClock, ImageStorage, IPublicationRepository

log = logging.getLogger("la_banca.ea03")


class LimpiarChatsExpiradosHandler:
    def __init__(self, chats: IChatRepository, imagenes: ImageStorage, clock: IClock,
                 publicaciones: IPublicationRepository | None = None) -> None:
        self._chats = chats
        self._imagenes = imagenes
        self._clock = clock
        self._publicaciones = publicaciones

    async def handle(self) -> dict[str, int]:
        ahora = self._clock.ahora()
        eliminados, referencias = await self._chats.eliminar_expirados(ahora)
        resultado = {"chats_eliminados": eliminados, "imagenes_eliminadas": await self._borrar(referencias, "chat expirado")}
        if self._publicaciones is not None:
            de_publicaciones = await self._publicaciones.retirar_imagenes_vencidas(ahora)
            resultado["imagenes_de_publicaciones_eliminadas"] = await self._borrar(de_publicaciones, "publicación vencida")
        return resultado

    async def _borrar(self, referencias: list[str], origen: str) -> int:
        borradas = 0
        for referencia in referencias:
            try:
                await self._imagenes.eliminar(referencia)
                borradas += 1
            except Exception:  # queda huérfana en el almacenamiento; no detiene el job
                log.exception("No se pudo eliminar una imagen de %s", origen)
        return borradas
