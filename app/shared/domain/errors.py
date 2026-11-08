"""Errores de dominio. Los handlers los lanzan; main.py los traduce a respuestas HTTP.

El mensaje es el texto literal exigido por el SRS v1.9 cuando este lo define.
"""


class ErrorDominio(Exception):
    status = 400
    codigo = "error"

    def __init__(self, mensaje: str, codigo: str | None = None, **extra) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        if codigo:
            self.codigo = codigo
        self.extra = extra


class ErrorValidacion(ErrorDominio):
    status = 422
    codigo = "validacion"


class NoAutenticado(ErrorDominio):
    status = 401
    codigo = "no_autenticado"


class Prohibido(ErrorDominio):
    status = 403
    codigo = "prohibido"


class NoEncontrado(ErrorDominio):
    status = 404
    codigo = "no_encontrado"


class Conflicto(ErrorDominio):
    status = 409
    codigo = "conflicto"


class NoDisponible(ErrorDominio):
    """El recurso existió pero ya no está activo (publicación vencida, chat expirado)."""

    status = 410
    codigo = "no_disponible"


class DemasiadosIntentos(ErrorDominio):
    status = 429
    codigo = "demasiados_intentos"
