"""Reglas de negocio puras compartidas (sin E/S). Fuente: SRS v1.9.

Las funciones `validar_*` devuelven el valor normalizado o lanzan ValueError con el mensaje del SRS,
de modo que pueden usarse tanto en los DTO Pydantic como en los handlers.
"""
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.shared.domain.entities import (
    FORMATOS_IMAGEN,
    INACTIVIDAD_CHAT,
    LONGITUD_CONTRASENA,
    LONGITUD_NICKNAME,
    TAMANO_MAX_IMAGEN,
    ClaveParametro,
    TipoDatoParametro,
)

_RE_NICKNAME = re.compile(r"^[A-Za-z0-9_]+$")
_RE_DOMINIO = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+$")


# --- Normalización (RN-32, RN-33) -------------------------------------------
def normalizar_texto(valor: str | None) -> str:
    """RN-32: elimina espacios iniciales y finales; un texto solo de espacios queda vacío."""
    return (valor or "").strip()


def normalizar_correo(correo: str) -> str:
    """RF-AUT-07 / RN-33: sin espacios extremos y en minúsculas."""
    return normalizar_texto(correo).lower()


def dominio_de(correo: str) -> str:
    return correo.rsplit("@", 1)[-1] if "@" in correo else ""


def correo_del_dominio(correo: str, dominio: str) -> bool:
    """RF-AUT-02: la parte tras «@» coincide exactamente (sin mayúsculas); un subdominio se rechaza."""
    return bool(_RE_CORREO.match(correo)) and dominio_de(correo).lower() == dominio.lower()


# --- Validaciones con mensajes del SRS --------------------------------------
def validar_nickname(nickname: str | None) -> str:
    valor = normalizar_texto(nickname)
    if not valor:
        raise ValueError("El nickname es obligatorio")  # RF-AUT-04
    minimo, maximo = LONGITUD_NICKNAME
    if not (minimo <= len(valor) <= maximo) or not _RE_NICKNAME.match(valor):
        raise ValueError(  # RF-AUT-05
            "El nickname debe tener de 3 a 20 caracteres: letras sin tilde, dígitos o guion bajo (_)"
        )
    return valor


def validar_contrasena(contrasena: str | None) -> str:
    """RF-AUT-14 / RN-30. La contraseña no se normaliza (distingue mayúsculas y espacios)."""
    valor = contrasena or ""
    minimo, maximo = LONGITUD_CONTRASENA
    if not (minimo <= len(valor) <= maximo):
        raise ValueError("La contraseña debe tener de 8 a 64 caracteres")
    if not any(c.isalpha() for c in valor):
        raise ValueError("La contraseña debe contener al menos una letra")
    if not any(c.isdigit() for c in valor):
        raise ValueError("La contraseña debe contener al menos un dígito")
    return valor


def validar_confirmacion(contrasena: str, confirmacion: str | None) -> None:
    if contrasena != (confirmacion or ""):
        raise ValueError("Las contraseñas no coinciden")  # RF-AUT-15


def validar_longitud(valor: str | None, minimo: int, maximo: int, campo: str) -> str:
    texto = normalizar_texto(valor)
    if not (minimo <= len(texto) <= maximo):
        if minimo > 0 and not texto:
            raise ValueError(f"Debes ingresar {campo[0].lower()}{campo[1:]}")
        raise ValueError(f"{campo} debe tener entre {minimo} y {maximo} caracteres")
    return texto


# --- Imágenes (RF-CHT-09, RF-CHT-26) -----------------------------------------
def detectar_formato_imagen(contenido: bytes) -> str | None:
    """Determina el MIME por la firma del contenido, no por la extensión (RF-CHT-26)."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(contenido) >= 12 and contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None


def validar_imagen(contenido: bytes) -> str:
    """Devuelve el MIME detectado o lanza ValueError."""
    if not contenido:
        raise ValueError("La imagen está vacía")
    if len(contenido) > TAMANO_MAX_IMAGEN:
        raise ValueError("La imagen supera el tamaño máximo de 5 MB")
    mime = detectar_formato_imagen(contenido)
    if mime not in FORMATOS_IMAGEN:
        raise ValueError("Formato de imagen no permitido. Usa JPG, PNG o WebP")
    return mime


# --- Tiempos -----------------------------------------------------------------
def segundos_restantes(vence: datetime, ahora: datetime) -> int:
    return max(0, int((vence - ahora).total_seconds()))


def minutos_hacia_arriba(delta: timedelta) -> int:
    """N de «… en N min» redondeado hacia arriba (RF-AUT-21, RF-CHT-14)."""
    return max(0, math.ceil(delta.total_seconds() / 60))


# --- Catálogo de parámetros (SRS §3.2) -----------------------------------------
@dataclass(frozen=True)
class DefinicionParametro:
    clave: ClaveParametro
    tipo: TipoDatoParametro
    valor_inicial: str | int | None  # None = sin valor inicial en el SRS: debe configurarse
    rango: dict
    unidad: str = ""


CATALOGO_PARAMETROS: dict[ClaveParametro, DefinicionParametro] = {
    d.clave: d
    for d in [
        # RF-CFG-01: el SRS deja el dominio «PENDIENTE DE DECISIÓN», no hay valor inicial.
        DefinicionParametro(ClaveParametro.DOMINIO_INSTITUCIONAL, TipoDatoParametro.STRING, None,
                            {"formato": "letras, dígitos, guiones y puntos; al menos un punto"}),
        DefinicionParametro(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS, TipoDatoParametro.INT, 3,
                            {"min": 1, "max": 10}),
        DefinicionParametro(ClaveParametro.ANTICIPACION_AVISO_CHAT_MIN, TipoDatoParametro.INT, 10,
                            {"min": 1, "max": 60}, "min"),
        DefinicionParametro(ClaveParametro.DIAS_RETENCION_REPORTES, TipoDatoParametro.INT, 7,
                            {"min": 1, "max": 30}, "días"),
        DefinicionParametro(ClaveParametro.HORAS_INACTIVIDAD_SESION, TipoDatoParametro.INT, 12,
                            {"min": 1, "max": 72}, "h"),
    ]
}


def validar_parametro(clave: ClaveParametro, valor_crudo: str | int) -> str | int:
    """RF-CFG-09 / CU-15 E1: valida tipo y rango. Lanza ValueError si no se puede aplicar."""
    definicion = CATALOGO_PARAMETROS[clave]
    if definicion.tipo is TipoDatoParametro.STRING:
        texto = normalizar_texto(str(valor_crudo)).lower()
        if not _RE_DOMINIO.match(texto) or len(texto) > 253:
            raise ValueError(f"{clave.value}: dominio con formato inválido ({texto!r})")
        return texto
    try:
        numero = int(str(valor_crudo).strip())
    except ValueError:
        raise ValueError(f"{clave.value}: se esperaba un entero ({valor_crudo!r})") from None
    minimo, maximo = definicion.rango["min"], definicion.rango["max"]
    if not (minimo <= numero <= maximo):
        raise ValueError(f"{clave.value}: {numero} fuera del rango {minimo}–{maximo}")
    if clave is ClaveParametro.ANTICIPACION_AVISO_CHAT_MIN and timedelta(minutes=numero) >= INACTIVIDAD_CHAT:
        raise ValueError(f"{clave.value}: la anticipación debe ser menor que la inactividad del chat")
    return numero


# --- Contenido de un mensaje del chat (RN-19, RF-CHT-08–10) ---------------------
def validar_contenido_mensaje(texto: str | None, imagen: bytes | None) -> tuple[str | None, str | None]:
    """Devuelve (texto normalizado | None, mime de la imagen | None). Exactamente uno de los dos."""
    from app.shared.domain.entities import LONGITUD_MENSAJE

    texto_normalizado = normalizar_texto(texto) or None
    if texto_normalizado and imagen:
        raise ValueError("Un mensaje lleva texto o una imagen, no ambos")
    if not texto_normalizado and not imagen:
        raise ValueError("Escribe un mensaje o adjunta una imagen")
    if texto_normalizado:
        if len(texto_normalizado) > LONGITUD_MENSAJE:
            raise ValueError(f"El mensaje debe tener entre 1 y {LONGITUD_MENSAJE} caracteres")
        return texto_normalizado, None
    return None, validar_imagen(imagen or b"")
