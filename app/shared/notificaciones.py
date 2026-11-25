"""Fase 5 — Aviso por correo a los administradores (ADMIN_EMAILS) cuando llega un reporte nuevo.

Es «mejor esfuerzo»: si el correo falla, el reporte igual queda guardado y aparece en el panel (/admin), cuyo
contador del menú también avisa a los administradores.
"""
import logging

from app.shared.config.moderacion import correos_admin
from app.shared.domain.contracts import IEmailSender

log = logging.getLogger("la_banca.avisos")


async def avisar_a_admins(correo: IEmailSender | None, resumen: str) -> None:
    if correo is None:
        return
    for destinatario in sorted(correos_admin()):
        try:
            await correo.enviar_aviso(destinatario, "Nuevo reporte en La Banca",
                                      f"{resumen}\n\nRevísalo en el panel de administración: /admin")
        except Exception:
            log.exception("No se pudo avisar a un administrador")
