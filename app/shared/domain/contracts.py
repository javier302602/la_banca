"""Contratos (ABC) del dominio. Los handlers dependen solo de este módulo.

Cada slice implementa en su repository.py únicamente los métodos que su handler usa
(segregación por slice); los demás conservan la implementación por defecto, que falla.
"""
import asyncio
from abc import ABC
from datetime import datetime

from app.shared.domain.entities import (
    Chat,
    ClaveParametro,
    EnlaceUnUso,
    EstadoSesion,
    Estudiante,
    IntentoAcceso,
    Mensaje,
    ParametroSistema,
    PropositoEnlace,
    Publicacion,
    Reporte,
    Sesion,
    TipoObjetoReportado,
    TipoPublicacion,
)


class IClock(ABC):
    def ahora(self) -> datetime:
        """Hora actual del servidor (UTC, con zona horaria)."""
        raise NotImplementedError


class IConfigurationProvider(ABC):
    def obtener(self, clave: ClaveParametro) -> ParametroSistema:
        raise NotImplementedError

    def obtener_todos(self) -> dict[ClaveParametro, ParametroSistema]:
        raise NotImplementedError

    def entero(self, clave: ClaveParametro) -> int:
        return int(self.obtener(clave).valor)

    def texto(self, clave: ClaveParametro) -> str:
        return str(self.obtener(clave).valor)


class IPasswordHasher(ABC):
    """`hash`/`verificar` son lentos a propósito (bcrypt, RNF-SEG-02). Desde código async se usan las variantes
    `_async`, que los ejecutan en un hilo para no bloquear el event loop del servidor mientras tanto."""

    def hash(self, contrasena: str) -> str:
        raise NotImplementedError

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        raise NotImplementedError

    async def hash_async(self, contrasena: str) -> str:
        return await asyncio.to_thread(self.hash, contrasena)

    async def verificar_async(self, contrasena: str, hash_guardado: str) -> bool:
        return await asyncio.to_thread(self.verificar, contrasena, hash_guardado)


class ITokenService(ABC):
    def generar(self) -> tuple[str, str]:
        """Devuelve (token_plano ≥ 128 bits, hash SHA-256). Solo el hash se persiste (RNF-SEG-08)."""
        raise NotImplementedError

    def hash(self, token_plano: str) -> str:
        raise NotImplementedError


class IEmailSender(ABC):
    """Envío de los únicos correos del MVP: enlaces de activación y de recuperación."""

    async def enviar_activacion(self, correo: str, nickname: str, enlace: str) -> None:
        """CU-01 / CU-17 — RF-AUT-28: el cuerpo contiene el enlace y el nickname."""
        raise NotImplementedError

    async def enviar_recuperacion(self, correo: str, enlace: str) -> None:
        """CU-18 — RF-AUT-36."""
        raise NotImplementedError


class ImageStorage(ABC):
    bucket: str = ""  # nombre del bucket, se guarda en messages.imageAttachment.storageBucket

    async def guardar(self, imagen: bytes, mime_type: str, prefijo: str = "chats") -> str:
        """Almacena la imagen sin metadatos EXIF (RNF-PRI-04) y devuelve su referencia (objectKey)."""
        raise NotImplementedError

    async def guardar_procesado(self, datos: bytes, mime_type: str, prefijo: str) -> str:
        """Almacena bytes ya validados y saneados por el slice (foto de perfil, documento) tal cual."""
        raise NotImplementedError

    async def copiar_a_retencion(self, referencia: str) -> str:
        """Copia la imagen de un chat reportado al área de retención y devuelve la nueva referencia."""
        raise NotImplementedError

    async def leer(self, referencia: str) -> bytes | None:
        """Bytes de la imagen; el acceso se autoriza antes en el slice (RNF-SEG-04)."""
        raise NotImplementedError

    async def eliminar(self, referencia: str) -> None:
        raise NotImplementedError


class IAccountRepository(ABC):
    # ESTUDIANTE (accounts)
    # Perfil (SRS v2.0): solo cuentas ACTIVE; el nickname se compara sin distinguir mayúsculas
    async def buscar_activa_por_nickname(self, nickname: str) -> Estudiante | None: raise NotImplementedError
    async def buscar_varias(self, ids: list[str]) -> dict[str, Estudiante]:
        """Cuentas por id (para pintar la foto o el avatar en el feed, el detalle y el chat)."""
        raise NotImplementedError
    async def actualizar_perfil(self, estudiante_id: str, biografia: str, avatar: str | None) -> None:
        raise NotImplementedError
    async def actualizar_foto(self, estudiante_id: str, foto: object | None) -> None:
        """Guarda (o quita, con None) la FotoPerfil de la cuenta."""
        raise NotImplementedError
    async def buscar_por_correo(self, correo: str) -> Estudiante | None: raise NotImplementedError
    async def buscar_por_id(self, estudiante_id: str) -> Estudiante | None: raise NotImplementedError
    async def existe_por_nickname(self, nickname: str, excluir_id: str | None = None) -> bool: raise NotImplementedError
    async def crear(self, estudiante: Estudiante) -> str:
        """Lanza Conflicto si el correo o el nickname ya existen (índices únicos)."""
        raise NotImplementedError
    async def eliminar(self, estudiante_id: str) -> None: raise NotImplementedError
    async def actualizar_nickname(self, estudiante_id: str, nickname: str) -> None:
        """Actualiza también las copias desnormalizadas (RF-AUT-26). Conflicto si ya está en uso."""
        raise NotImplementedError
    async def eliminar_no_activadas(self, registradas_antes_de: datetime) -> int: raise NotImplementedError
    # Enlaces de un solo uso (subdocumentos activation / passwordReset)
    async def registrar_enlace(self, estudiante_id: str, proposito: PropositoEnlace, enlace: EnlaceUnUso) -> None:
        """Reemplaza el token vigente (RF-AUT-46 / RF-AUT-50) y guarda el historial de envíos."""
        raise NotImplementedError
    async def activar_con_enlace(self, token_hash: str, ahora: datetime) -> Estudiante | None:
        """Atómico: activa la cuenta pendiente con token vigente e invalida el token (RNF-SEG-09)."""
        raise NotImplementedError
    async def restablecer_con_enlace(self, token_hash: str, password_hash: str, ahora: datetime) -> Estudiante | None:
        """Atómico: cambia la contraseña de la cuenta activa con token vigente e invalida el token."""
        raise NotImplementedError
    # INTENTO_ACCESO (login_attempts)
    async def obtener_intento(self, correo: str) -> IntentoAcceso | None: raise NotImplementedError
    async def guardar_intento(self, intento: IntentoAcceso) -> None: raise NotImplementedError
    async def reiniciar_intentos(self, correo: str) -> None: raise NotImplementedError
    # SESION (sessions)
    async def crear_sesion(self, sesion: Sesion) -> str: raise NotImplementedError
    async def buscar_sesion_por_token(self, token_hash: str) -> Sesion | None: raise NotImplementedError
    async def registrar_interaccion(self, sesion_id: str, ahora: datetime, expira_en: datetime) -> None: raise NotImplementedError
    async def finalizar_sesion(self, sesion_id: str, estado: EstadoSesion, ahora: datetime) -> None: raise NotImplementedError
    async def cerrar_sesiones_de(self, estudiante_id: str, ahora: datetime) -> int: raise NotImplementedError
    async def eliminar_sesiones_vencidas(self, vencidas_antes_de: datetime) -> int:
        """Borra las sesiones (activas vencidas, cerradas o expiradas) con vencimiento anterior al corte."""
        raise NotImplementedError


class IPublicationRepository(ABC):
    async def retirar_imagenes_vencidas(self, ahora: datetime) -> list[str]:
        """SRS v2.0: vacía las imágenes de las publicaciones vencidas o cerradas; devuelve sus referencias."""
        raise NotImplementedError

    async def contar_activas_por_usuario(self, autor_id: str, ahora: datetime) -> int: raise NotImplementedError
    async def crear(self, publicacion: Publicacion) -> str: raise NotImplementedError
    async def crear_si_hay_cupo(self, publicacion: Publicacion, maximo: int, ahora: datetime) -> str | None:
        """Atómico: crea solo si el autor tiene menos de `maximo` activas (RF-PUB-06). Id o None si no hay cupo.

        Debe serializar las creaciones simultáneas del mismo autor (otra pestaña u otro dispositivo)."""
        raise NotImplementedError
    async def listar_activas_por_usuario(self, autor_id: str, ahora: datetime) -> list[Publicacion]: raise NotImplementedError
    async def buscar_por_id(self, publicacion_id: str) -> Publicacion | None: raise NotImplementedError
    async def cerrar(self, publicacion_id: str, autor_id: str, ahora: datetime) -> bool:
        """Cierra solo si sigue activa y pertenece al autor. True si se cerró."""
        raise NotImplementedError
    async def listar_feed(
        self, ahora: datetime, tipo: TipoPublicacion | None, cursor: str | None, limite: int
    ) -> tuple[list[Publicacion], str | None]:
        """Activas al consultar (EA-02), más recientes primero; devuelve (bloque, siguiente_cursor)."""
        raise NotImplementedError


class IChatRepository(ABC):
    async def buscar_por_usuario_y_publicacion(self, respondedor_id: str, publicacion_id: str) -> Chat | None: raise NotImplementedError
    async def crear_con_primer_mensaje(self, chat: Chat, primer_mensaje: Mensaje) -> str:
        """Atómico (RNF-FIA-03). Lanza Conflicto si ya existe un chat del respondedor sobre la publicación."""
        raise NotImplementedError
    async def eliminar_chat(self, chat_id: str) -> list[str]:
        """Elimina el chat y sus mensajes; devuelve las referencias de imagen a borrar."""
        raise NotImplementedError
    async def listar_activos_por_usuario(self, usuario_id: str, ahora: datetime) -> list[Chat]: raise NotImplementedError
    async def buscar_por_id(self, chat_id: str) -> Chat | None: raise NotImplementedError
    async def listar_mensajes(self, chat_id: str, despues_de: datetime | None = None) -> list[Mensaje]: raise NotImplementedError
    async def buscar_mensaje(self, chat_id: str, mensaje_id: str) -> Mensaje | None: raise NotImplementedError
    async def agregar_mensaje(self, mensaje: Mensaje, nueva_expiracion: datetime) -> str | None:
        """Atómico: inserta y reinicia la expiración solo si el chat sigue activo. Id del mensaje o None."""
        raise NotImplementedError
    async def marcar_leido(self, chat_id: str, usuario_id: str, ahora: datetime) -> None: raise NotImplementedError
    async def eliminar_expirados(self, ahora: datetime) -> tuple[int, list[str]]:
        """Borra chats expirados y sus mensajes; devuelve (chats eliminados, referencias de imagen a borrar)."""
        raise NotImplementedError


class IReportRepository(ABC):
    async def crear(self, reporte: Reporte) -> str:
        """Inserta el reporte con su ContenidoReportado embebido en una sola operación (RNF-FIA-03)."""
        raise NotImplementedError
    async def existe_reporte(self, reportante_id: str, tipo: TipoObjetoReportado, objeto_id: str) -> bool: raise NotImplementedError
    async def eliminar_vencidos(self, ahora: datetime) -> tuple[int, list[str]]:
        """Purga REPORTE + CONTENIDO_REPORTADO vencidos; devuelve (reportes eliminados, imágenes retenidas)."""
        raise NotImplementedError


class IParameterRepository(ABC):
    """Registro de los valores efectivos en system_parameters (CU-15)."""

    async def guardar(self, parametro: ParametroSistema) -> None: raise NotImplementedError
