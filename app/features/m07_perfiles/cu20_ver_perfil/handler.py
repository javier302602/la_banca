"""CU-20 — Ver el perfil de una persona. Caso de uso (handler).

SRS v2.0, cambio 2.1: con sesión iniciada se ve el nickname, la foto o el avatar, la biografía y la fecha de
ingreso (activación) de cualquier cuenta activa. El correo no se muestra a nadie. Una cuenta pendiente de
activación o inexistente responde lo mismo («no existe»), para no revelar qué nicknames están registrados.
"""
from app.shared.domain.contracts import IAccountRepository, ImageStorage
from app.shared.domain.errors import NoEncontrado
from app.shared.domain.perfiles import apariencia

from .request import FotoDescargada, PerfilPublicoResponse

MSG_NO_EXISTE = "Este perfil no existe"


class VerPerfilHandler:
    def __init__(self, cuentas: IAccountRepository, imagenes: ImageStorage) -> None:
        self._cuentas = cuentas
        self._imagenes = imagenes

    async def handle(self, estudiante_id: str, nickname: str) -> PerfilPublicoResponse:
        e = await self._cuentas.buscar_activa_por_nickname(nickname)
        if e is None:
            raise NoEncontrado(MSG_NO_EXISTE, codigo="perfil_inexistente")
        return PerfilPublicoResponse(nickname=e.nickname, biografia=e.biografia, fecha_ingreso=e.fecha_ingreso,
                                     apariencia=apariencia(e.id, e.nickname, e.foto, e.avatar),
                                     es_propio=e.id == estudiante_id)

    async def foto(self, nickname: str) -> FotoDescargada:
        e = await self._cuentas.buscar_activa_por_nickname(nickname)
        contenido = await self._imagenes.leer(e.foto.referencia) if e and e.foto else None
        if contenido is None:
            raise NoEncontrado("La foto no existe", codigo="foto_inexistente")
        return FotoDescargada(contenido, e.foto.mime_type)
