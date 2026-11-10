"""Crea una cuenta ya activada, con los términos vigentes aceptados (p. ej. la primera cuenta tras desplegar).

Uso (dentro del contenedor de la app):
    docker compose exec app python -m scripts.crear_usuario --correo ana@unas.edu.pe --nickname ana_07
La contraseña se pide por teclado (o se lee de la variable NUEVA_CONTRASENA, para automatizar).
Aplica las mismas reglas que el registro: dominio institucional, formato del nickname, longitud de la contraseña,
correo y nickname únicos (sin distinguir mayúsculas).
"""
import argparse
import asyncio
import getpass
import os
import sys
from datetime import datetime, timezone


async def crear(correo: str, nickname: str, contrasena: str) -> str:
    from app.features.m01_acceso.cu01_registrar_cuenta.repository import MongoRegistrarCuentaRepository
    from app.shared.config.provider import get_config, variable
    from app.shared.db.mongo import asegurar_indices_una_vez, base_de_datos
    from app.shared.domain.entities import AceptacionTerminos, ClaveParametro, EnlaceUnUso, EstadoCuenta, Estudiante
    from app.shared.domain.reglas import normalizar_correo, validar_contrasena, validar_nickname
    from app.shared.security.hashing import BcryptPasswordHasher

    correo = normalizar_correo(correo)
    dominio = get_config().texto(ClaveParametro.DOMINIO_INSTITUCIONAL)
    if not correo.endswith("@" + dominio.lower()):
        raise ValueError(f"El correo debe ser del dominio institucional @{dominio}")
    nickname, contrasena = validar_nickname(nickname), validar_contrasena(contrasena)
    await asegurar_indices_una_vez()
    ahora = datetime.now(timezone.utc)
    hash_ = await asyncio.to_thread(BcryptPasswordHasher().hash, contrasena)
    cuenta = Estudiante("", correo, hash_, nickname, EstadoCuenta.ACTIVA, ahora,
                        AceptacionTerminos(variable("TERMINOS_VERSION", "pendiente"), ahora),
                        activacion=EnlaceUnUso(None, None, [ahora]), fecha_activacion=ahora)  # como tras el registro
    return await MongoRegistrarCuentaRepository(base_de_datos()).crear(cuenta)


def main(argv=None) -> int:
    analizador = argparse.ArgumentParser(description="Crea una cuenta activa de La Banca")
    analizador.add_argument("--correo", required=True)
    analizador.add_argument("--nickname", required=True)
    args = analizador.parse_args(argv)
    contrasena = os.environ.get("NUEVA_CONTRASENA") or getpass.getpass("Contraseña (8 a 64 caracteres): ")
    try:
        cuenta_id = asyncio.run(crear(args.correo, args.nickname, contrasena))
    except Exception as error:  # ValueError de validación o Conflicto por duplicado
        print(f"No se creó la cuenta: {getattr(error, 'mensaje', error)}", file=sys.stderr)
        return 1
    print(f"Cuenta creada y activada: @{args.nickname} (id {cuenta_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
