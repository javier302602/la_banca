"""Entidades del dominio alineadas con el MER (3FN) del Entregable 2 — 10 entidades.

ESTUDIANTE, INTENTO_ACCESO, SESION, PUBLICACION, CHAT, MENSAJE, MOTIVO_REPORTE, REPORTE,
CONTENIDO_REPORTADO y PARAMETRO_SISTEMA. Los valores de los Enum coinciden con los CHECK IN
del diccionario de datos (Tablas 6.1–6.8). Constantes fijas: sección 3.3 del SRS v1.9.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# --- Constantes fijas (SRS §3.3) ----------------------------------------------
DURACION_PUBLICACION = timedelta(hours=24)            # RN-09
INACTIVIDAD_CHAT = timedelta(hours=24)                # RN-20
VIGENCIA_ENLACE_ACTIVACION = timedelta(hours=24)      # RN-41
PLAZO_CUENTA_NO_ACTIVADA = timedelta(hours=72)        # RN-43
MAX_ENLACES_24H = 5                                   # RN-42 (activación) / RN-50 (recuperación)
VENTANA_ENLACES = timedelta(hours=24)                 # ventana móvil de RN-42 / RN-50
VIGENCIA_ENLACE_RECUPERACION = timedelta(minutes=30)  # RN-46
INTENTOS_FALLIDOS_BLOQUEO = 5                         # RN-39
VENTANA_INTENTOS_FALLIDOS = timedelta(minutes=15)     # RN-39
DURACION_BLOQUEO_LOGIN = timedelta(minutes=15)        # RN-39 / EA-06
TAMANO_BLOQUE_FEED = 20                               # RN-29
RETENCION_SESIONES = timedelta(days=30)               # Entregable 2 §7.3: se conservan los últimos 30 días

LONGITUD_NICKNAME = (3, 20)
PATRON_NICKNAME = r"^[A-Za-z0-9_]+$"
LONGITUD_CONTRASENA = (8, 64)
LONGITUD_TITULO = (1, 80)
LONGITUD_DESCRIPCION = (1, 500)
LONGITUD_MENSAJE = 500
LONGITUD_OBSERVACION = 300
FORMATOS_IMAGEN = ("image/jpeg", "image/png", "image/webp")
TAMANO_MAX_IMAGEN = 5 * 1024 * 1024  # 5 242 880 bytes


# --- Enumeraciones (valores = CHECK IN del Entregable 2) --------------------
class EstadoCuenta(str, Enum):
    PENDIENTE_ACTIVACION = "PENDIENTE_ACTIVACION"
    ACTIVA = "ACTIVA"


class EstadoSesion(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class TipoPublicacion(str, Enum):
    NECESITO = "NECESITO"
    OFREZCO = "OFREZCO"
    ACTIVIDAD = "ACTIVIDAD"


class EstadoPublicacion(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class EstadoChat(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"


class TipoObjetoReportado(str, Enum):
    PUBLICATION = "PUBLICATION"
    CHAT = "CHAT"


class CodigoMotivo(str, Enum):
    """Los 5 motivos predefinidos (DD-05). Catálogo maestro: MOTIVOS_REPORTE."""

    INAPPROPRIATE = "INAPPROPRIATE"
    HARASSMENT = "HARASSMENT"
    SPAM = "SPAM"
    FRAUD = "FRAUD"
    OTHER = "OTHER"


class PropositoEnlace(str, Enum):
    ACTIVACION = "ACTIVACION"
    RECUPERACION = "RECUPERACION"


class TipoDatoParametro(str, Enum):
    STRING = "STRING"
    INT = "INT"
    ARRAY = "ARRAY"


class ClaveParametro(str, Enum):
    DOMINIO_INSTITUCIONAL = "DOMINIO_INSTITUCIONAL"                      # RF-CFG-01
    MAX_PUBLICACIONES_ACTIVAS = "CFG_MAX_PUBLICACIONES_ACTIVAS"          # RF-CFG-03
    ANTICIPACION_AVISO_CHAT_MIN = "CFG_ANTICIPACION_AVISO_CHAT_MIN"      # RF-CFG-05
    DIAS_RETENCION_REPORTES = "CFG_DIAS_RETENCION_REPORTES"              # RF-CFG-06
    HORAS_INACTIVIDAD_SESION = "CFG_HORAS_INACTIVIDAD_SESION"            # RF-CFG-07


# --- Objetos de valor embebidos ---------------------------------------------
@dataclass
class EnlaceUnUso:
    """Subdocumento activation / passwordReset de ESTUDIANTE. Solo se guarda el hash SHA-256.

    `envios_en` guarda los instantes de envío para aplicar la ventana móvil de 24 h (RN-42/RN-50);
    `envios` (sentCount del Entregable 2) es la cantidad de envíos dentro de esa ventana.
    """

    token_hash: str | None = None
    expira_en: datetime | None = None
    envios_en: list[datetime] = field(default_factory=list)

    def envios_en_ventana(self, ahora: datetime) -> int:
        return sum(1 for t in self.envios_en if t > ahora - VENTANA_ENLACES)

    @property
    def envios(self) -> int:
        return len(self.envios_en)


@dataclass
class AceptacionTerminos:
    """RF-AUT-17: versión y fecha/hora de aceptación de términos y política."""

    version: str
    fecha: datetime


@dataclass
class ImagenAdjunta:
    """Subdocumento imageAttachment de MENSAJE (metadatos del objeto en ImageStorage)."""

    referencia: str    # objectKey en el bucket
    mime_type: str     # FORMATOS_IMAGEN
    tamano_bytes: int  # 1 .. TAMANO_MAX_IMAGEN
    bucket: str | None = None  # storageBucket (Entregable 2 §5.3)


# --- Entidades (10) -----------------------------------------------------------
@dataclass
class Estudiante:
    """1. ESTUDIANTE — colección accounts (Tabla 6.1)."""

    id: str
    correo_institucional: str  # interno (RN-04): nunca se expone en DTOs de respuesta
    password_hash: str
    nickname: str
    estado: EstadoCuenta
    fecha_registro: datetime
    aceptacion: AceptacionTerminos | None = None
    activacion: EnlaceUnUso = field(default_factory=EnlaceUnUso)
    recuperacion: EnlaceUnUso = field(default_factory=EnlaceUnUso)
    fecha_activacion: datetime | None = None

    def pendiente_vencida(self, ahora: datetime) -> bool:
        """EA-07 evaluado al consultar: cuenta pendiente con más de 72 h ya no existe (RN-43)."""
        return (self.estado is EstadoCuenta.PENDIENTE_ACTIVACION
                and ahora >= self.fecha_registro + PLAZO_CUENTA_NO_ACTIVADA)


@dataclass
class IntentoAcceso:
    """2. INTENTO_ACCESO — colección login_attempts (Tabla 6.2). Por correo, exista o no la cuenta (PA-27).

    `fallos` guarda los instantes de los fallos consecutivos que siguen dentro de la ventana móvil de
    15 min (como máximo 5): conteo_fallidos = len(fallos), primer_fallo = fallos[0] (RN-39).
    """

    correo_ingresado: str
    conteo_fallidos: int  # 1..5
    primer_fallo: datetime
    ultimo_fallo: datetime
    bloqueado_hasta: datetime | None = None  # 5.º fallo + 15 min (RN-39)
    id: str | None = None
    fallos: list[datetime] = field(default_factory=list)

    def registrar_fallo(self, ahora: datetime) -> None:
        """Ventana móvil (RF-AUT-19): descarta los fallos con más de 15 min y agrega el actual."""
        recientes = [t for t in self.fallos if t > ahora - VENTANA_INTENTOS_FALLIDOS]
        self.fallos = (recientes + [ahora])[-INTENTOS_FALLIDOS_BLOQUEO:]
        self.conteo_fallidos = len(self.fallos)
        self.primer_fallo = self.fallos[0]
        self.ultimo_fallo = ahora
        if self.conteo_fallidos >= INTENTOS_FALLIDOS_BLOQUEO:
            self.bloqueado_hasta = ahora + DURACION_BLOQUEO_LOGIN


@dataclass
class Sesion:
    """3. SESION — colección sessions (Tabla 6.3)."""

    id: str
    estudiante_id: str
    token_hash: str
    fecha_inicio: datetime
    ultima_interaccion: datetime
    fecha_expiracion: datetime  # ultima_interaccion + CFG_HORAS_INACTIVIDAD_SESION (EA-01)
    estado: EstadoSesion = EstadoSesion.ACTIVE
    fecha_cierre: datetime | None = None


@dataclass
class Publicacion:
    """4. PUBLICACION — colección publications (Tabla 6.4)."""

    id: str
    autor_id: str
    nickname_autor: str  # desnormalizado para el feed
    tipo: TipoPublicacion
    titulo: str
    descripcion: str
    fecha_creacion: datetime
    fecha_expiracion: datetime  # fecha_creacion + DURACION_PUBLICACION (RN-09)
    estado: EstadoPublicacion = EstadoPublicacion.ACTIVE
    fecha_cierre: datetime | None = None

    def activa(self, ahora: datetime) -> bool:
        """EA-02 evaluado al consultar."""
        return self.estado is EstadoPublicacion.ACTIVE and ahora < self.fecha_expiracion


@dataclass
class Chat:
    """5. CHAT — colección chats (Tabla 6.5). Único por (publicacion_id, respondedor_id)."""

    id: str
    publicacion_id: str
    autor_id: str
    respondedor_id: str  # distinto de autor_id
    fecha_inicio: datetime
    ultima_actividad: datetime
    fecha_expiracion: datetime  # ultima_actividad + INACTIVIDAD_CHAT (RN-20)
    # Contexto desnormalizado para la cabecera aunque la publicación expire (RF-CHT-22)
    tipo_publicacion: TipoPublicacion = TipoPublicacion.NECESITO
    titulo_publicacion: str = ""
    nickname_autor: str = ""
    nickname_respondedor: str = ""
    ultima_lectura: dict[str, datetime] = field(default_factory=dict)  # RF-CHT-21
    estado: EstadoChat = EstadoChat.ACTIVE

    @property
    def participantes(self) -> tuple[str, str]:
        return (self.autor_id, self.respondedor_id)

    def activo(self, ahora: datetime) -> bool:
        """EA-03 evaluado al consultar."""
        return self.estado is EstadoChat.ACTIVE and ahora < self.fecha_expiracion

    def contraparte(self, usuario_id: str) -> tuple[str, str]:
        """(id, nickname) del interlocutor."""
        if usuario_id == self.autor_id:
            return self.respondedor_id, self.nickname_respondedor
        return self.autor_id, self.nickname_autor

    def tiene_no_leidos(self, usuario_id: str) -> bool:
        leido = self.ultima_lectura.get(usuario_id)
        return leido is None or self.ultima_actividad > leido


@dataclass
class Mensaje:
    """6. MENSAJE — colección messages (Tabla 6.6). Texto o imagen, no ambos (RN-19)."""

    id: str
    chat_id: str
    emisor_id: str
    nickname_emisor: str  # desnormalizado para el render del chat
    fecha_envio: datetime
    texto: str | None = None
    imagen: ImagenAdjunta | None = None


@dataclass
class MotivoReporte:
    """7. MOTIVO_REPORTE — catálogo maestro de los 5 motivos (3FN)."""

    codigo: CodigoMotivo
    nombre: str
    descripcion: str = ""
    activo: bool = True


MOTIVOS_REPORTE: dict[CodigoMotivo, MotivoReporte] = {
    m.codigo: m
    for m in [  # RF-REP-03
        MotivoReporte(CodigoMotivo.INAPPROPRIATE, "Contenido inapropiado"),
        MotivoReporte(CodigoMotivo.HARASSMENT, "Acoso o comportamiento ofensivo"),
        MotivoReporte(CodigoMotivo.SPAM, "Spam"),
        MotivoReporte(CodigoMotivo.FRAUD, "Fraude o engaño"),
        MotivoReporte(CodigoMotivo.OTHER, "Otro"),
    ]
}


@dataclass
class ContenidoReportado:
    """9. CONTENIDO_REPORTADO — instantánea inmutable 1:1 con REPORTE (subdocumento reportedContentSnapshot).

    `mensajes` usa las claves del Entregable 2 (messageId, senderId, senderNickname, text, imageKey, sentAt).
    `datos_publicacion` es la copia de la publicación reportada (RF-REP-06) o, en un chat, el contexto de su
    publicación de origen.
    """

    usuario_reportado_id: str
    mensajes: list[dict] = field(default_factory=list)
    snapshot_imagenes: list[str] = field(default_factory=list)  # claves protegidas en ImageStorage
    datos_publicacion: dict | None = None
    capturado_en: datetime | None = None


@dataclass
class Reporte:
    """8. REPORTE — colección reports (Tabla 6.7)."""

    id: str
    reportante_id: str
    tipo_objeto: TipoObjetoReportado
    objeto_id: str
    codigo_motivo: CodigoMotivo
    fecha_reporte: datetime
    fecha_retencion_fin: datetime  # fecha_reporte + CFG_DIAS_RETENCION_REPORTES (EA-05)
    contenido: ContenidoReportado
    observacion: str | None = None


@dataclass
class ParametroSistema:
    """10. PARAMETRO_SISTEMA — colección system_parameters + variables de entorno (Tabla 6.8)."""

    clave: ClaveParametro
    valor: str | int | list[str]
    tipo_dato: TipoDatoParametro
    rango_permitido: dict
    fecha_actualizacion: datetime
