"""CU-19 — Editar mi perfil. Caso de uso (handler).

SRS v2.0, cambios 2.1–2.3 (docs/cambios_v2.md):
- Biografía de hasta 160 caracteres y avatar elegido del catálogo (o ninguno: iniciales sobre un color).
- Foto opcional JPG/PNG/WebP ≤ 2 MB: el formato se detecta por la firma del contenido, se decodifica y se
  vuelve a codificar sin EXIF, recortada al cuadrado central (WebP de 512 px como máximo). La foto
  anterior se borra del almacenamiento al reemplazarla o quitarla.
- No se infiere ni se guarda el género: solo el identificador del avatar elegido.
"""
import asyncio

from app.shared.domain.contracts import IAccountRepository, IClock, ImageStorage
from app.shared.domain.entities import Estudiante
from app.shared.domain.errors import ErrorValidacion, NoEncontrado
from app.shared.domain.perfiles import LADO_FOTO, TAMANO_MAX_FOTO, FotoPerfil, apariencia
from app.shared.domain.reglas import detectar_formato_imagen
from app.shared.storage.image_storage import foto_cuadrada

from .request import EditarPerfilRequest, MiPerfilResponse

PREFIJO_FOTOS = "perfiles"
MSG_FOTO_GRANDE = "La foto supera el tamaño máximo de 2 MB"
MSG_FOTO_FORMATO = "Formato de imagen no permitido. Usa JPG, PNG o WebP"


class EditarPerfilHandler:
    def __init__(self, cuentas: IAccountRepository, imagenes: ImageStorage, clock: IClock) -> None:
        self._cuentas = cuentas
        self._imagenes = imagenes
        self._clock = clock

    async def ver(self, estudiante_id: str) -> MiPerfilResponse:
        return self._respuesta(await self._cuenta(estudiante_id))

    async def actualizar(self, estudiante_id: str, body: EditarPerfilRequest) -> MiPerfilResponse:
        await self._cuenta(estudiante_id)
        await self._cuentas.actualizar_perfil(estudiante_id, body.biografia, body.avatar)
        return await self.ver(estudiante_id)

    async def subir_foto(self, estudiante_id: str, contenido: bytes | None) -> MiPerfilResponse:
        if not contenido:
            raise ErrorValidacion("Selecciona una foto", codigo="foto_vacia", campo="foto")
        if len(contenido) > TAMANO_MAX_FOTO:
            raise ErrorValidacion(MSG_FOTO_GRANDE, codigo="foto_grande", campo="foto")
        mime = detectar_formato_imagen(contenido)
        if mime is None:
            raise ErrorValidacion(MSG_FOTO_FORMATO, codigo="foto_formato", campo="foto")
        anterior = (await self._cuenta(estudiante_id)).foto
        try:
            limpia = await asyncio.to_thread(foto_cuadrada, contenido, mime, LADO_FOTO)
        except ErrorValidacion as e:
            raise ErrorValidacion(e.mensaje, codigo="foto_invalida", campo="foto") from None
        referencia = await self._imagenes.guardar_procesado(limpia, "image/webp", PREFIJO_FOTOS)
        try:
            await self._cuentas.actualizar_foto(estudiante_id,
                                                FotoPerfil(referencia, "image/webp", self._clock.ahora()))
        except Exception:
            await self._imagenes.eliminar(referencia)
            raise
        if anterior is not None:
            await self._imagenes.eliminar(anterior.referencia)
        return await self.ver(estudiante_id)

    async def quitar_foto(self, estudiante_id: str) -> MiPerfilResponse:
        anterior = (await self._cuenta(estudiante_id)).foto
        if anterior is not None:
            await self._cuentas.actualizar_foto(estudiante_id, None)
            await self._imagenes.eliminar(anterior.referencia)
        return await self.ver(estudiante_id)

    async def _cuenta(self, estudiante_id: str) -> Estudiante:
        e = await self._cuentas.buscar_por_id(estudiante_id)
        if e is None:
            raise NoEncontrado("La cuenta no existe", codigo="cuenta_inexistente")
        return e

    @staticmethod
    def _respuesta(e: Estudiante) -> MiPerfilResponse:
        return MiPerfilResponse(nickname=e.nickname, biografia=e.biografia, avatar=e.avatar,
                                tiene_foto=e.foto is not None, apariencia=apariencia(e.id, e.nickname, e.foto, e.avatar),
                                fecha_ingreso=e.fecha_ingreso)
