"""Implementaciones de IEmailSender (enlaces de activación CU-01/CU-17 y de recuperación CU-18).

- `ConsoleEmailSender`: guarda los correos en memoria y los escribe en el registro (desarrollo y pruebas).
- `SmtpEmailSender`: SMTP con STARTTLS.
Se elige con EMAIL_SENDER=consola|smtp.
"""
import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.shared.config.provider import variable
from app.shared.domain.contracts import IEmailSender

log = logging.getLogger("la_banca.email")


@dataclass
class CorreoEnviado:
    destinatario: str
    asunto: str
    cuerpo: str
    enlace: str


def _cuerpo_activacion(nickname: str, enlace: str) -> str:
    return (f"Hola {nickname}:\n\nPara activar tu cuenta de La Banca abre este enlace "
            f"(vigente 24 horas, de un solo uso):\n\n{enlace}\n\n"
            "Si no creaste esta cuenta, ignora este mensaje.")


def _cuerpo_recuperacion(enlace: str) -> str:
    return ("Recibimos una solicitud para cambiar la contraseña de tu cuenta de La Banca.\n\n"
            f"Abre este enlace (vigente 30 minutos, de un solo uso):\n\n{enlace}\n\n"
            "Si no lo solicitaste, ignora este mensaje.")


class ConsoleEmailSender(IEmailSender):
    def __init__(self) -> None:
        self.enviados: list[CorreoEnviado] = []

    async def enviar_activacion(self, correo: str, nickname: str, enlace: str) -> None:
        self._registrar(CorreoEnviado(correo, "Activa tu cuenta de La Banca",
                                      _cuerpo_activacion(nickname, enlace), enlace))

    async def enviar_recuperacion(self, correo: str, enlace: str) -> None:
        self._registrar(CorreoEnviado(correo, "Cambia tu contraseña de La Banca",
                                      _cuerpo_recuperacion(enlace), enlace))

    def _registrar(self, correo: CorreoEnviado) -> None:
        self.enviados.append(correo)
        log.info("[correo de desarrollo] %s -> %s", correo.asunto, correo.enlace)


class SmtpEmailSender(IEmailSender):
    def __init__(self, host: str, puerto: int, usuario: str | None, clave: str | None, remitente: str) -> None:
        self._host, self._puerto = host, puerto
        self._usuario, self._clave, self._remitente = usuario, clave, remitente

    async def enviar_activacion(self, correo: str, nickname: str, enlace: str) -> None:
        await self._enviar(correo, "Activa tu cuenta de La Banca", _cuerpo_activacion(nickname, enlace))

    async def enviar_recuperacion(self, correo: str, enlace: str) -> None:
        await self._enviar(correo, "Cambia tu contraseña de La Banca", _cuerpo_recuperacion(enlace))

    async def _enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        mensaje = EmailMessage()
        mensaje["From"], mensaje["To"], mensaje["Subject"] = self._remitente, destinatario, asunto
        mensaje.set_content(cuerpo)
        await asyncio.to_thread(self._enviar_sincrono, mensaje)

    def _enviar_sincrono(self, mensaje: EmailMessage) -> None:
        with smtplib.SMTP(self._host, self._puerto, timeout=15) as smtp:
            smtp.starttls()
            if self._usuario:
                smtp.login(self._usuario, self._clave or "")
            smtp.send_message(mensaje)


_emisor: IEmailSender | None = None


def get_email_sender() -> IEmailSender:
    global _emisor
    if _emisor is None:
        if variable("EMAIL_SENDER", "consola") == "smtp":
            host, remitente = variable("SMTP_HOST"), variable("SMTP_FROM")
            if not host or not remitente:
                raise RuntimeError("Faltan SMTP_HOST o SMTP_FROM")
            _emisor = SmtpEmailSender(host, int(variable("SMTP_PORT", "587")), variable("SMTP_USER"),
                                      variable("SMTP_PASSWORD"), remitente)
        else:
            _emisor = ConsoleEmailSender()
    return _emisor


def url_base() -> str:
    """URL pública de la app para construir los enlaces de los correos."""
    return (variable("APP_BASE_URL", "http://localhost:8000") or "").rstrip("/")
