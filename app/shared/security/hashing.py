"""Hash de contraseñas (bcrypt) y tokens aleatorios de un solo uso."""
import base64
import hashlib
import secrets

import bcrypt

from app.shared.domain.contracts import IPasswordHasher, ITokenService

COSTO_BCRYPT = 12  # Entregable 2, Tabla 6.1 (factor ≥ 12); RNF-SEG-02 exige ≥ 10


def _prehash(contrasena: str) -> bytes:
    """bcrypt solo usa 72 bytes: una contraseña de 64 caracteres Unicode puede superar ese límite.
    Se deriva primero un SHA-256 en base64 (44 bytes) para que todos los caracteres cuenten."""
    return base64.b64encode(hashlib.sha256(contrasena.encode("utf-8")).digest())


class BcryptPasswordHasher(IPasswordHasher):
    def __init__(self, costo: int = COSTO_BCRYPT) -> None:
        self._costo = costo

    def hash(self, contrasena: str) -> str:
        return bcrypt.hashpw(_prehash(contrasena), bcrypt.gensalt(rounds=self._costo)).decode("ascii")

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            return bcrypt.checkpw(_prehash(contrasena), hash_guardado.encode("ascii"))
        except ValueError:
            return False


class SecureTokenService(ITokenService):
    """Tokens de 256 bits con `secrets` (RNF-SEG-06/08); se persiste solo su SHA-256."""

    BYTES = 32

    def generar(self) -> tuple[str, str]:
        plano = secrets.token_urlsafe(self.BYTES)
        return plano, self.hash(plano)

    def hash(self, token_plano: str) -> str:
        return hashlib.sha256(token_plano.encode("utf-8")).hexdigest()
