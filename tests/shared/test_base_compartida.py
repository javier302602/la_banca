"""Fase 0 — base compartida: reglas, reloj, hashing, configuración, imágenes, correo y sesión."""
import asyncio
import io
import logging
from datetime import timedelta

import pytest
from PIL import Image

from app.shared.clock import FakeClock, SystemClock
from app.shared.config.provider import ConfiguracionFaltante, EnvConfigurationProvider
from app.shared.domain import reglas
from app.shared.domain.entities import ClaveParametro, EstadoSesion, Sesion
from app.shared.domain.errors import ErrorValidacion, NoAutenticado
from app.shared.email.sender import ConsoleEmailSender
from app.shared.security.hashing import BcryptPasswordHasher, SecureTokenService
from app.shared.security.session import MENSAJE_INACTIVIDAD, ValidadorSesion
from app.shared.storage.image_storage import MemoryImageStorage
from tests.fakes import FakeAccountRepository, FakeConfig, estudiante


# --- reglas -------------------------------------------------------------------------
def test_normalizacion_y_dominio():
    assert reglas.normalizar_correo("  Ana@UNAS.edu.pe ") == "ana@unas.edu.pe"
    assert reglas.correo_del_dominio("ana@unas.edu.pe", "UNAS.edu.pe")
    assert not reglas.correo_del_dominio("ana@fiis.unas.edu.pe", "unas.edu.pe")  # subdominio (RF-AUT-02)
    assert not reglas.correo_del_dominio("ana@gmail.com", "unas.edu.pe")
    assert reglas.normalizar_texto("   ") == ""


@pytest.mark.parametrize("nick", ["abc", "Ana_07", "a" * 20])
def test_nickname_valido(nick):
    assert reglas.validar_nickname(f" {nick} ") == nick


@pytest.mark.parametrize("nick", ["ab", "a" * 21, "ana 07", "año", "josé", "ana.07", "ana-07"])
def test_nickname_invalido(nick):
    with pytest.raises(ValueError):
        reglas.validar_nickname(nick)


def test_nickname_vacio_es_obligatorio():
    with pytest.raises(ValueError, match="obligatorio"):
        reglas.validar_nickname("  ")


@pytest.mark.parametrize("clave,mensaje", [("abc1234", "8 a 64"), ("a" * 65 + "1", "8 a 64"),
                                           ("12345678", "letra"), ("abcdefgh", "dígito")])
def test_politica_contrasena(clave, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        reglas.validar_contrasena(clave)
    assert reglas.validar_contrasena("clave123") == "clave123"


def test_confirmacion():
    with pytest.raises(ValueError, match="Las contraseñas no coinciden"):
        reglas.validar_confirmacion("clave123", "clave124")


def _imagen(formato: str, exif: bool = False) -> bytes:
    img = Image.new("RGB", (8, 8), "red")
    buf = io.BytesIO()
    if exif:
        datos = img.getexif()
        datos[0x010F] = "CamaraEspia"  # Make
        datos[0x8825] = {1: "S", 2: (9.0, 17.0, 0.0)}  # GPSInfo
        img.save(buf, format=formato, exif=datos)
    else:
        img.save(buf, format=formato)
    return buf.getvalue()


@pytest.mark.parametrize("formato,mime", [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")])
def test_detecta_formato_por_contenido(formato, mime):
    assert reglas.validar_imagen(_imagen(formato)) == mime


def test_rechaza_formato_y_tamano():
    with pytest.raises(ValueError, match="Formato"):
        reglas.validar_imagen(b"GIF89a....")
    with pytest.raises(ValueError, match="5 MB"):
        reglas.validar_imagen(b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024))


def test_minutos_hacia_arriba():
    assert reglas.minutos_hacia_arriba(timedelta(minutes=9, seconds=1)) == 10
    assert reglas.minutos_hacia_arriba(timedelta(minutes=10)) == 10


# --- reloj --------------------------------------------------------------------------
def test_hora_hhmm_en_america_lima():
    """RF-CHT-11 / RN-34: HH:MM en la hora del sistema, también al cruzar la medianoche."""
    from datetime import datetime, timezone

    from app.shared.clock import hora_hhmm

    assert hora_hhmm(datetime(2026, 10, 3, 3, 30, tzinfo=timezone.utc)) == "22:30"
    assert hora_hhmm(datetime(2026, 10, 2, 17, 5, tzinfo=timezone.utc)) == "12:05"
    assert hora_hhmm(datetime(2026, 10, 2, 17, 5)) == "12:05"  # valor sin zona: se asume UTC


def test_relojes():
    assert SystemClock().ahora().tzinfo is not None
    reloj = FakeClock()
    inicio = reloj.ahora()
    assert reloj.avanzar(hours=24) - inicio == timedelta(hours=24)


# --- hashing ------------------------------------------------------------------------
def test_bcrypt_con_sal_y_contrasena_larga():
    hasher = BcryptPasswordHasher(costo=4)
    larga = "ñ" * 63 + "1"  # 127 bytes en UTF-8: supera el límite de 72 bytes de bcrypt
    h1, h2 = hasher.hash(larga), hasher.hash(larga)
    assert h1 != h2 and larga not in h1  # sal distinta (RNF-SEG-02)
    assert hasher.verificar(larga, h1)
    assert not hasher.verificar("ñ" * 62 + "x1", h1)
    assert not hasher.verificar("x", "no-es-bcrypt")


def test_costo_por_defecto_es_12():
    assert BcryptPasswordHasher().hash("clave123").startswith("$2b$12$")


def test_tokens_de_128_bits_o_mas_y_unicos():
    servicio = SecureTokenService()
    tokens = {servicio.generar()[0] for _ in range(100)}
    assert len(tokens) == 100  # RNF-SEG-08
    plano, hash_ = servicio.generar()
    assert len(plano) >= 22 and hash_ == servicio.hash(plano) and plano not in hash_


# --- configuración ------------------------------------------------------------------
def test_config_valores_iniciales_del_srs():
    proveedor = EnvConfigurationProvider({"DOMINIO_INSTITUCIONAL": "unas.edu.pe"})
    assert proveedor.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS) == 3
    assert proveedor.entero(ClaveParametro.ANTICIPACION_AVISO_CHAT_MIN) == 10
    assert proveedor.entero(ClaveParametro.DIAS_RETENCION_REPORTES) == 7
    assert proveedor.entero(ClaveParametro.HORAS_INACTIVIDAD_SESION) == 12
    assert proveedor.texto(ClaveParametro.DOMINIO_INSTITUCIONAL) == "unas.edu.pe"


def test_config_dominio_sin_valor_inicial():
    with pytest.raises(ConfiguracionFaltante):
        EnvConfigurationProvider({}).obtener(ClaveParametro.DOMINIO_INSTITUCIONAL)


def test_config_fuera_de_rango_conserva_ultimo_valido(caplog):
    entorno = {"CFG_MAX_PUBLICACIONES_ACTIVAS": "5"}
    proveedor = EnvConfigurationProvider(entorno)
    assert proveedor.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS) == 5
    entorno["CFG_MAX_PUBLICACIONES_ACTIVAS"] = "11"
    with caplog.at_level(logging.ERROR):
        assert proveedor.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS) == 5  # RF-CFG-09
    assert "fuera del rango" in caplog.text
    entorno["CFG_MAX_PUBLICACIONES_ACTIVAS"] = "dos"
    assert proveedor.entero(ClaveParametro.MAX_PUBLICACIONES_ACTIVAS) == 5


def test_config_invalido_sin_previo_usa_valor_inicial():
    proveedor = EnvConfigurationProvider({"CFG_HORAS_INACTIVIDAD_SESION": "0"})
    assert proveedor.entero(ClaveParametro.HORAS_INACTIVIDAD_SESION) == 12


# --- imágenes -------------------------------------------------------------------------
def test_imagen_se_recodifica_sin_exif():
    almacen = MemoryImageStorage()
    original = _imagen("JPEG", exif=True)
    assert b"CamaraEspia" in original
    clave = asyncio.run(almacen.guardar(original, "image/jpeg"))
    guardada = asyncio.run(almacen.leer(clave))
    assert b"CamaraEspia" not in guardada
    with Image.open(io.BytesIO(guardada)) as img:
        assert img.format == "JPEG" and len(img.getexif()) == 0


def test_imagen_corrupta_con_firma_valida_se_rechaza():
    almacen = MemoryImageStorage()
    truncada = _imagen("PNG")[:40]  # firma PNG correcta pero contenido incompleto
    assert reglas.validar_imagen(truncada) == "image/png"
    with pytest.raises(ErrorValidacion):
        asyncio.run(almacen.guardar(truncada, "image/png"))
    with pytest.raises(ErrorValidacion):
        asyncio.run(almacen.guardar(b"\xff\xd8\xff" + b"basura" * 10, "image/jpeg"))


def test_imagen_copia_retencion_y_eliminacion():
    almacen = MemoryImageStorage()
    clave = asyncio.run(almacen.guardar(_imagen("PNG"), "image/png"))
    copia = asyncio.run(almacen.copiar_a_retencion(clave))
    assert copia.startswith("reports/") and copia.endswith(".png")
    asyncio.run(almacen.eliminar(clave))
    assert asyncio.run(almacen.leer(clave)) is None and asyncio.run(almacen.leer(copia))


# --- correo ---------------------------------------------------------------------------
def test_correo_de_activacion_incluye_enlace_y_nickname():
    emisor = ConsoleEmailSender()
    asyncio.run(emisor.enviar_activacion("ana@unas.edu.pe", "ana_07", "https://x/activar?token=abc"))
    correo = emisor.enviados[0]
    assert "ana_07" in correo.cuerpo and "https://x/activar?token=abc" in correo.cuerpo  # RF-AUT-28


# --- sesión (EA-01) ---------------------------------------------------------------------
def _sesion_activa(repo: FakeAccountRepository, reloj: FakeClock, horas: int = 12) -> str:
    cuenta_id = asyncio.run(repo.crear(estudiante()))
    plano, hash_ = SecureTokenService().generar()
    ahora = reloj.ahora()
    asyncio.run(repo.crear_sesion(Sesion("", cuenta_id, hash_, ahora, ahora, ahora + timedelta(hours=horas))))
    return plano


def test_sesion_valida_reinicia_conteo_por_interaccion():
    repo, reloj = FakeAccountRepository(), FakeClock()
    token = _sesion_activa(repo, reloj)
    validador = ValidadorSesion(repo, FakeConfig(), reloj)
    reloj.avanzar(hours=11)
    actual = asyncio.run(validador.validar(token, es_interaccion=True))
    assert actual.nickname == "ana_07"
    reloj.avanzar(hours=11)  # 22 h desde el inicio, 11 h desde la última interacción
    asyncio.run(validador.validar(token))


def test_actualizacion_automatica_no_reinicia_conteo():
    repo, reloj = FakeAccountRepository(), FakeClock()
    token = _sesion_activa(repo, reloj)
    validador = ValidadorSesion(repo, FakeConfig(), reloj)
    reloj.avanzar(hours=11)
    asyncio.run(validador.validar(token, es_interaccion=False))  # RF-AUT-25
    reloj.avanzar(hours=1, minutes=1)
    with pytest.raises(NoAutenticado) as error:
        asyncio.run(validador.validar(token, es_interaccion=False))
    assert error.value.mensaje == MENSAJE_INACTIVIDAD  # RF-AUT-23


def test_cambio_de_inactividad_aplica_desde_la_siguiente_interaccion():
    """RF-CFG-11: una sesión existente conserva su vencimiento; la siguiente interacción aplica el valor nuevo."""
    repo, reloj = FakeAccountRepository(), FakeClock()
    token = _sesion_activa(repo, reloj)  # creada con 12 h
    config = FakeConfig()
    validador = ValidadorSesion(repo, config, reloj)
    config.valores[ClaveParametro.HORAS_INACTIVIDAD_SESION] = 2
    reloj.avanzar(hours=5)
    asyncio.run(validador.validar(token, es_interaccion=False))  # sigue vigente: conserva las 12 h originales
    asyncio.run(validador.validar(token))  # interacción: ahora vence en 2 h
    assert next(iter(repo.sesiones.values())).fecha_expiracion == reloj.ahora() + timedelta(hours=2)
    reloj.avanzar(hours=2, minutes=1)
    with pytest.raises(NoAutenticado) as error:
        asyncio.run(validador.validar(token))
    assert error.value.mensaje == MENSAJE_INACTIVIDAD


def test_sesion_expirada_queda_invalidada():
    repo, reloj = FakeAccountRepository(), FakeClock()
    token = _sesion_activa(repo, reloj)
    validador = ValidadorSesion(repo, FakeConfig(), reloj)
    reloj.avanzar(hours=12)
    with pytest.raises(NoAutenticado):
        asyncio.run(validador.validar(token))
    assert next(iter(repo.sesiones.values())).estado is EstadoSesion.EXPIRED  # RNF-SEG-07


def test_sin_token_o_token_desconocido():
    validador = ValidadorSesion(FakeAccountRepository(), FakeConfig(), FakeClock())
    for token in (None, "desconocido"):
        with pytest.raises(NoAutenticado):
            asyncio.run(validador.validar(token))


# --- verificación del entorno de producción ---------------------------------------------
from app.shared.config.provider import ConfiguracionInvalida, verificar_entorno  # noqa: E402


@pytest.mark.parametrize("entorno", [{}, {"ENTORNO": "desarrollo"}, {"ENTORNO": "produccion", "IMAGE_STORAGE": "s3",
                                                                     "EMAIL_SENDER": "smtp"}])
def test_entorno_valido(entorno):
    verificar_entorno(entorno)


@pytest.mark.parametrize("entorno,falta", [
    ({"ENTORNO": "produccion"}, ["IMAGE_STORAGE=memoria", "EMAIL_SENDER=consola"]),
    ({"ENTORNO": "Produccion", "IMAGE_STORAGE": "s3", "EMAIL_SENDER": "consola"}, ["EMAIL_SENDER=consola"]),
    ({"ENTORNO": "produccion", "IMAGE_STORAGE": "memoria", "EMAIL_SENDER": "smtp"}, ["IMAGE_STORAGE=memoria"]),
])
def test_produccion_rechaza_proveedores_de_desarrollo(entorno, falta):
    with pytest.raises(ConfiguracionInvalida) as error:
        verificar_entorno(entorno)
    for texto in falta:
        assert texto in str(error.value)


def test_la_app_no_inicia_en_produccion_con_memoria():
    import os
    import subprocess
    import sys

    env = {**os.environ, "ENTORNO": "produccion", "IMAGE_STORAGE": "memoria", "EMAIL_SENDER": "consola"}
    proceso = subprocess.run([sys.executable, "-c", "import app.main"], env=env, capture_output=True, text=True,
                             timeout=60)
    assert proceso.returncode != 0
    assert "Configuración inválida para ENTORNO=produccion" in proceso.stderr and "usa IMAGE_STORAGE=s3" in proceso.stderr
