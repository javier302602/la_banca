"""Perfiles (SRS v2.0, cambios 2.1–2.4 de docs/cambios_v2.md).

Lo que ven los demás de una persona: nickname, foto o avatar, biografía y fecha de ingreso. El correo
institucional nunca sale de la cuenta (RN-04 modificada).

Apariencia (en este orden):
1. la foto que subió (JPG/PNG/WebP ≤ 2 MB, recortada a cuadrado, sin EXIF y re-codificada);
2. el avatar predefinido que eligió (`avatar-01`…`avatar-12`);
3. sus iniciales sobre un color.

No se infiere ni se guarda el género: se guarda solo el identificador del avatar elegido. La agrupación
«hombre / mujer / neutro» existe únicamente para presentar las opciones en pantalla. El color de las
iniciales se deriva del identificador interno de la cuenta, no de ningún atributo personal.
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel

BIOGRAFIA_MAX = 160
TAMANO_MAX_FOTO = 2 * 1024 * 1024  # 2 097 152 bytes
LADO_FOTO = 512                     # px del cuadrado guardado
COLORES_INICIALES = 6               # --lb-color-avatar-1 … -6 en tokens.css

# Solo presentación: el grupo no se guarda (cambio 2.3).
GRUPOS_AVATAR: dict[str, tuple[str, ...]] = {
    "hombre": tuple(f"avatar-{n:02d}" for n in range(1, 5)),
    "mujer": tuple(f"avatar-{n:02d}" for n in range(5, 9)),
    "neutro": tuple(f"avatar-{n:02d}" for n in range(9, 13)),
}
AVATARES: tuple[str, ...] = tuple(a for grupo in GRUPOS_AVATAR.values() for a in grupo)


@dataclass(frozen=True)
class FotoPerfil:
    referencia: str      # objectKey en el almacenamiento (prefijo perfiles/)
    mime_type: str
    actualizada_en: datetime


class Apariencia(BaseModel):
    """Lo que la interfaz pinta junto al nickname: foto, avatar o iniciales."""

    tipo: Literal["foto", "avatar", "iniciales"]
    url: str | None = None
    iniciales: str
    color: int  # 1..COLORES_INICIALES


def iniciales(nickname: str) -> str:
    """Hasta dos letras del nickname: separa por «_», «.», «-» o por cambio de minúscula a mayúscula."""
    partes, actual = [], ""
    for i, c in enumerate(nickname):
        if c in "_.-":
            if actual:
                partes.append(actual)
            actual = ""
        elif c.isupper() and i and nickname[i - 1].islower():
            partes.append(actual)
            actual = c
        else:
            actual += c
    if actual:
        partes.append(actual)
    letras = [p[0] for p in partes if p and p[0].isalnum()]
    if len(letras) >= 2:
        return (letras[0] + letras[1]).upper()
    limpio = [c for c in nickname if c.isalnum()]
    return "".join(limpio[:2]).upper() or "?"


def color_de(estudiante_id: str) -> int:
    resumen = hashlib.sha256(estudiante_id.encode()).digest()
    return resumen[0] % COLORES_INICIALES + 1


def url_foto(nickname: str, foto: FotoPerfil) -> str:
    version = int(foto.actualizada_en.timestamp())
    return f"/api/perfiles/{quote(nickname)}/foto?v={version}"


def apariencia(estudiante_id: str, nickname: str, foto: FotoPerfil | None = None,
               avatar: str | None = None) -> Apariencia:
    base = {"iniciales": iniciales(nickname), "color": color_de(estudiante_id)}
    if foto is not None:
        return Apariencia(tipo="foto", url=url_foto(nickname, foto), **base)
    if avatar in AVATARES:
        return Apariencia(tipo="avatar", url=f"/static/avatares/{avatar}.svg", **base)
    return Apariencia(tipo="iniciales", **base)


async def apariencias(cuentas, nicknames: dict[str, str]) -> dict[str, Apariencia]:
    """Apariencia de varias cuentas a la vez ({id: nickname} → {id: Apariencia}) con una sola consulta.

    `cuentas` es un IAccountRepository; si es None (pruebas de otros casos de uso) se usan las iniciales.
    """
    encontradas = await cuentas.buscar_varias(list(nicknames)) if cuentas is not None and nicknames else {}
    resultado = {}
    for estudiante_id, nickname in nicknames.items():
        e = encontradas.get(estudiante_id)
        resultado[estudiante_id] = (apariencia(e.id, e.nickname, e.foto, e.avatar) if e
                                    else apariencia(estudiante_id, nickname))
    return resultado
