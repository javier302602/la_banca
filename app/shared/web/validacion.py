"""Mensajes de validación en español (RNF-USA-05).

FastAPI/Pydantic generan mensajes en inglés («Field required», «Input should be …»). Las validaciones propias
de los DTO ya lanzan ValueError con el mensaje del SRS; este módulo traduce el resto según el tipo de error.
"""
from typing import Any

# Nombres legibles de los campos de la API
NOMBRES_CAMPO = {
    "correo": "correo", "contrasena": "contraseña", "confirmacion": "confirmación de la contraseña",
    "nickname": "nickname", "acepta_terminos": "aceptación de los términos", "tipo": "tipo", "titulo": "título",
    "descripcion": "descripción", "texto": "mensaje", "imagen": "imagen", "codigo_motivo": "motivo",
    "observacion": "observación", "token": "enlace", "cursor": "cursor", "despues_de": "fecha de referencia",
}


def _campo(loc: tuple | list) -> str:
    partes = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie", "form")]
    if not partes:
        return "cuerpo de la solicitud"
    return NOMBRES_CAMPO.get(partes[-1], partes[-1])


def _opciones(esperado: str) -> str:
    return esperado.replace("'", "").replace(" or ", " o ")


def mensaje_en_espanol(error: dict[str, Any]) -> str:
    """Mensaje en español para un error de `ValidationError.errors()`."""
    tipo = error.get("type", "")
    ctx = error.get("ctx") or {}
    campo = _campo(error.get("loc", ()))
    if tipo == "value_error":  # validadores propios: el mensaje ya es el del SRS
        return str(error.get("msg", "")).removeprefix("Value error, ") or "Dato inválido"
    if tipo == "missing":
        return f"El campo «{campo}» es obligatorio"
    if tipo in ("enum", "literal_error"):
        return f"El campo «{campo}» admite solo: {_opciones(str(ctx.get('expected', '')))}"
    if tipo == "string_too_long":
        return f"El campo «{campo}» admite como máximo {ctx.get('max_length')} caracteres"
    if tipo == "string_too_short":
        return f"El campo «{campo}» debe tener al menos {ctx.get('min_length')} caracteres"
    if tipo in ("string_type", "string_unicode"):
        return f"El campo «{campo}» debe ser un texto"
    if tipo in ("bool_type", "bool_parsing"):
        return f"El campo «{campo}» debe ser verdadero o falso"
    if tipo in ("int_type", "int_parsing", "int_from_float", "float_type", "float_parsing"):
        return f"El campo «{campo}» debe ser un número"
    if tipo.startswith(("datetime_", "date_")):
        return f"El campo «{campo}» debe ser una fecha y hora válida"
    if tipo == "json_invalid":
        return "El cuerpo de la solicitud no es un JSON válido"
    if tipo in ("model_type", "model_attributes_type", "dict_type"):
        return "El cuerpo de la solicitud debe ser un objeto JSON"
    if tipo in ("bytes_type", "bytes_too_long"):
        return f"El campo «{campo}» no es un archivo válido"
    return f"El campo «{campo}» no es válido"
