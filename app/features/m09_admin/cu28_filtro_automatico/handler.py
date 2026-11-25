"""CU-28 — Filtro automático de palabras ofensivas. Caso de uso (servicio).

Lo llaman crear publicación (CU-05), responder publicación (CU-10) y enviar mensaje (CU-11) DESPUÉS de guardar.
Si el texto tiene alguna palabra de config/palabras_ofensivas.json, crea un reporte PENDIENTE marcado como
automático (motivo «contenido obsceno o inapropiado») y avisa por correo a los administradores. No bloquea ni
borra nada: decide un administrador. Si algo falla aquí, el envío del usuario no se ve afectado.
"""
import logging
from datetime import timedelta

from app.shared.config.moderacion import palabras_ofensivas
from app.shared.domain.contracts import IClock, IConfigurationProvider, IEmailSender
from app.shared.domain.entities import ClaveParametro, Mensaje, Publicacion
from app.shared.notificaciones import avisar_a_admins

from .repository import MongoFiltroRepository

log = logging.getLogger("la_banca.cu28")


class FiltroAutomatico:
    def __init__(self, reportes: MongoFiltroRepository, config: IConfigurationProvider, clock: IClock,
                 correo: IEmailSender | None = None) -> None:
        self._reportes = reportes
        self._config = config
        self._clock = clock
        self._correo = correo

    async def revisar_publicacion(self, p: Publicacion) -> list[str]:
        palabras = palabras_ofensivas(f"{p.titulo}\n{p.descripcion}")
        if palabras:
            datos = {"publicationId": p.id, "type": p.tipo.value, "title": p.titulo, "description": p.descripcion,
                     "authorNickname": p.nickname_autor, "createdAt": p.fecha_creacion, "expiresAt": p.fecha_expiracion,
                     "imageKeys": []}
            await self._reportar("PUBLICATION", p.id, p.autor_id, palabras, datos, [])
        return palabras

    async def revisar_mensaje(self, chat_id: str, m: Mensaje) -> list[str]:
        palabras = palabras_ofensivas(m.texto)
        if palabras:
            copia = {"messageId": m.id, "senderId": m.emisor_id, "senderNickname": m.nickname_emisor, "text": m.texto,
                     "imageKey": None, "sticker": None, "document": None, "sentAt": m.fecha_envio}
            await self._reportar("CHAT", chat_id, m.emisor_id, palabras, None, [copia])
        return palabras

    async def _reportar(self, tipo, objeto_id, ofensor_id, palabras, publicacion, mensajes) -> None:
        try:
            ahora = self._clock.ahora()
            dias = self._config.entero(ClaveParametro.DIAS_RETENCION_REPORTES)
            await self._reportes.crear_reporte_automatico(tipo, objeto_id, ofensor_id, palabras, publicacion, mensajes,
                                                          ahora, ahora + timedelta(days=dias))
            await avisar_a_admins(self._correo, f"El filtro automático marcó un contenido ({tipo.lower()}) "
                                                f"por: {', '.join(palabras)}.")
        except Exception:  # el filtro nunca impide publicar o enviar
            log.exception("No se pudo crear el reporte automático")
