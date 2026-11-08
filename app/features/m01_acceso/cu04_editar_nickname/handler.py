"""CU-04 — Editar nickname. Caso de uso (handler).

RF: RF-AUT-05, RF-AUT-06, RF-AUT-13, RF-AUT-26, RF-AUT-27
Valida formato y unicidad sin distinguir mayúsculas (se permite cambiar solo las mayúsculas del propio).
El repositorio actualiza las copias desnormalizadas en publicaciones, chats y mensajes (RF-AUT-26) y el
nickname anterior queda libre de inmediato (RF-AUT-27).
"""
from app.shared.domain.contracts import IAccountRepository, IClock
from app.shared.domain.errors import Conflicto

from .request import EditarNicknameRequest, NicknameResponse

MSG_NICKNAME_OCUPADO = "Ese nickname ya está en uso. Elige otro"


class EditarNicknameHandler:
    def __init__(self, cuentas: IAccountRepository, clock: IClock) -> None:
        self._cuentas = cuentas
        self._clock = clock

    async def handle(self, estudiante_id: str, body: EditarNicknameRequest) -> NicknameResponse:
        if await self._cuentas.existe_por_nickname(body.nickname, excluir_id=estudiante_id):
            raise Conflicto(MSG_NICKNAME_OCUPADO, codigo="nickname_ocupado")
        try:
            await self._cuentas.actualizar_nickname(estudiante_id, body.nickname)
        except Conflicto:
            raise Conflicto(MSG_NICKNAME_OCUPADO, codigo="nickname_ocupado") from None
        return NicknameResponse(nickname=body.nickname)
