"""Fakes en memoria de los contratos del dominio para las pruebas de handlers (sin Mongo real)."""
import copy
import itertools
from dataclasses import replace
from datetime import datetime

from app.shared.clock import FakeClock  # noqa: F401  (re-exportado para las pruebas)
from app.shared.domain.contracts import (
    IAccountRepository,
    IChatRepository,
    IConfigurationProvider,
    IParameterRepository,
    IPasswordHasher,
    IPublicationRepository,
    IReportRepository,
)
from app.shared.domain.entities import (
    Chat,
    ClaveParametro,
    EnlaceUnUso,
    EstadoChat,
    EstadoCuenta,
    EstadoPublicacion,
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
from app.shared.domain.errors import Conflicto
from app.shared.domain.reglas import CATALOGO_PARAMETROS
from app.shared.email.sender import ConsoleEmailSender
from app.shared.security.hashing import SecureTokenService  # noqa: F401
from app.shared.storage.image_storage import MemoryImageStorage

_ids = itertools.count(1)


def nuevo_id() -> str:
    return f"{next(_ids):024x}"


class FakeEmailSender(ConsoleEmailSender):
    pass


class FakeImageStorage(MemoryImageStorage):
    pass


class FakePasswordHasher(IPasswordHasher):
    """Hash trivial y rápido; las pruebas de bcrypt real están en tests/shared."""

    def hash(self, contrasena: str) -> str:
        return "hash::" + contrasena[::-1]

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        return hash_guardado == self.hash(contrasena)


class FakeConfig(IConfigurationProvider):
    def __init__(self, dominio: str = "unas.edu.pe", **valores) -> None:
        self.valores: dict[ClaveParametro, str | int] = {
            clave: d.valor_inicial for clave, d in CATALOGO_PARAMETROS.items() if d.valor_inicial is not None
        }
        self.valores[ClaveParametro.DOMINIO_INSTITUCIONAL] = dominio
        for nombre, valor in valores.items():
            self.valores[ClaveParametro[nombre]] = valor

    def obtener(self, clave: ClaveParametro) -> ParametroSistema:
        d = CATALOGO_PARAMETROS[clave]
        return ParametroSistema(clave, self.valores[clave], d.tipo, d.rango, datetime(2026, 1, 1))

    def obtener_todos(self):
        return {c: self.obtener(c) for c in self.valores}


class FakeAccountRepository(IAccountRepository):
    def __init__(self) -> None:
        self.cuentas: dict[str, Estudiante] = {}
        self.intentos: dict[str, IntentoAcceso] = {}
        self.sesiones: dict[str, Sesion] = {}
        self.nickname_cambios: list[tuple[str, str]] = []

    # cuentas
    async def buscar_por_correo(self, correo):
        return next((copy.deepcopy(e) for e in self.cuentas.values() if e.correo_institucional == correo), None)

    async def buscar_por_id(self, estudiante_id):
        e = self.cuentas.get(estudiante_id)
        return copy.deepcopy(e) if e else None

    async def existe_por_nickname(self, nickname, excluir_id=None):
        return any(e.nickname.lower() == nickname.lower() and e.id != excluir_id for e in self.cuentas.values())

    async def crear(self, estudiante):
        if any(e.correo_institucional == estudiante.correo_institucional for e in self.cuentas.values()):
            raise Conflicto("correo duplicado", codigo="correo_duplicado")
        if await self.existe_por_nickname(estudiante.nickname):
            raise Conflicto("nickname duplicado", codigo="nickname_duplicado")
        estudiante = copy.deepcopy(estudiante)
        estudiante.id = estudiante.id or nuevo_id()
        self.cuentas[estudiante.id] = estudiante
        return estudiante.id

    async def eliminar(self, estudiante_id):
        self.cuentas.pop(estudiante_id, None)

    async def buscar_activa_por_nickname(self, nickname):
        return next((copy.deepcopy(e) for e in self.cuentas.values()
                     if e.nickname.lower() == nickname.lower() and e.estado is EstadoCuenta.ACTIVA), None)

    async def buscar_varias(self, ids):
        return {i: copy.deepcopy(self.cuentas[i]) for i in ids if i in self.cuentas}

    async def actualizar_perfil(self, estudiante_id, biografia, avatar):
        self.cuentas[estudiante_id].biografia = biografia
        self.cuentas[estudiante_id].avatar = avatar

    async def actualizar_foto(self, estudiante_id, foto):
        self.cuentas[estudiante_id].foto = foto

    async def actualizar_nickname(self, estudiante_id, nickname):
        if await self.existe_por_nickname(nickname, excluir_id=estudiante_id):
            raise Conflicto("nickname duplicado", codigo="nickname_duplicado")
        self.cuentas[estudiante_id].nickname = nickname
        self.nickname_cambios.append((estudiante_id, nickname))

    async def eliminar_no_activadas(self, registradas_antes_de):
        borrar = [i for i, e in self.cuentas.items()
                  if e.estado is EstadoCuenta.PENDIENTE_ACTIVACION and e.fecha_registro <= registradas_antes_de]
        for i in borrar:
            del self.cuentas[i]
        return len(borrar)

    # enlaces
    async def registrar_enlace(self, estudiante_id, proposito, enlace):
        e = self.cuentas[estudiante_id]
        if proposito is PropositoEnlace.ACTIVACION:
            e.activacion = copy.deepcopy(enlace)
        else:
            e.recuperacion = copy.deepcopy(enlace)

    async def activar_con_enlace(self, token_hash, ahora):
        for e in self.cuentas.values():
            a = e.activacion
            if (e.estado is EstadoCuenta.PENDIENTE_ACTIVACION and a.token_hash == token_hash
                    and a.expira_en and ahora < a.expira_en):
                e.estado, e.fecha_activacion = EstadoCuenta.ACTIVA, ahora
                e.activacion = replace(a, token_hash=None, expira_en=None)
                return copy.deepcopy(e)
        return None

    async def restablecer_con_enlace(self, token_hash, password_hash, ahora):
        for e in self.cuentas.values():
            r = e.recuperacion
            if e.estado is EstadoCuenta.ACTIVA and r.token_hash == token_hash and r.expira_en and ahora < r.expira_en:
                e.password_hash = password_hash
                e.recuperacion = replace(r, token_hash=None, expira_en=None)
                return copy.deepcopy(e)
        return None

    # intentos
    async def obtener_intento(self, correo):
        i = self.intentos.get(correo)
        return copy.deepcopy(i) if i else None

    async def guardar_intento(self, intento):
        self.intentos[intento.correo_ingresado] = copy.deepcopy(intento)

    async def reiniciar_intentos(self, correo):
        self.intentos.pop(correo, None)

    # sesiones
    async def crear_sesion(self, sesion):
        sesion = copy.deepcopy(sesion)
        sesion.id = sesion.id or nuevo_id()
        self.sesiones[sesion.id] = sesion
        return sesion.id

    async def buscar_sesion_por_token(self, token_hash):
        s = next((s for s in self.sesiones.values() if s.token_hash == token_hash), None)
        return copy.deepcopy(s) if s else None

    async def registrar_interaccion(self, sesion_id, ahora, expira_en):
        s = self.sesiones[sesion_id]
        if s.estado is EstadoSesion.ACTIVE:
            s.ultima_interaccion, s.fecha_expiracion = ahora, expira_en

    async def finalizar_sesion(self, sesion_id, estado, ahora):
        s = self.sesiones.get(sesion_id)
        if s and s.estado is EstadoSesion.ACTIVE:
            s.estado, s.fecha_cierre = estado, ahora

    async def cerrar_sesiones_de(self, estudiante_id, ahora):
        n = 0
        for s in self.sesiones.values():
            if s.estudiante_id == estudiante_id and s.estado is EstadoSesion.ACTIVE:
                s.estado, s.fecha_cierre = EstadoSesion.CLOSED, ahora
                n += 1
        return n

    async def eliminar_sesiones_vencidas(self, vencidas_antes_de):
        borrar = [i for i, s in self.sesiones.items() if s.fecha_expiracion <= vencidas_antes_de]
        for i in borrar:
            del self.sesiones[i]
        return len(borrar)


class FakePublicationRepository(IPublicationRepository):
    def __init__(self) -> None:
        self.publicaciones: dict[str, Publicacion] = {}
        self._orden: dict[str, int] = {}

    def _activas(self, ahora):
        return [p for p in self.publicaciones.values() if p.activa(ahora)]

    async def contar_activas_por_usuario(self, autor_id, ahora):
        return sum(1 for p in self._activas(ahora) if p.autor_id == autor_id)

    async def retirar_imagenes_vencidas(self, ahora):
        claves = []
        for p in self.publicaciones.values():
            if p.imagenes and not p.activa(ahora):
                claves += [i.referencia for i in p.imagenes]
                p.imagenes = []
        return claves

    async def crear(self, publicacion):
        publicacion = copy.deepcopy(publicacion)
        publicacion.id = publicacion.id or nuevo_id()
        self.publicaciones[publicacion.id] = publicacion
        self._orden[publicacion.id] = len(self._orden)
        return publicacion.id

    async def crear_si_hay_cupo(self, publicacion, maximo, ahora):
        if await self.contar_activas_por_usuario(publicacion.autor_id, ahora) >= maximo:
            return None
        return await self.crear(publicacion)

    def _clave(self, p):
        return (p.fecha_creacion, self._orden[p.id])

    async def listar_activas_por_usuario(self, autor_id, ahora):
        propias = [copy.deepcopy(p) for p in self._activas(ahora) if p.autor_id == autor_id]
        return sorted(propias, key=self._clave, reverse=True)

    async def buscar_por_id(self, publicacion_id):
        p = self.publicaciones.get(publicacion_id)
        return copy.deepcopy(p) if p else None

    async def cerrar(self, publicacion_id, autor_id, ahora):
        p = self.publicaciones.get(publicacion_id)
        if not p or p.autor_id != autor_id or not p.activa(ahora):
            return False
        p.estado, p.fecha_cierre = EstadoPublicacion.CLOSED, ahora
        return True

    async def listar_feed(self, ahora, tipo, cursor, limite):
        lista = sorted((p for p in self._activas(ahora) if tipo is None or p.tipo is tipo),
                       key=self._clave, reverse=True)
        inicio = int(cursor) if cursor else 0
        bloque = lista[inicio:inicio + limite]
        siguiente = str(inicio + limite) if inicio + limite < len(lista) else None
        return [copy.deepcopy(p) for p in bloque], siguiente


class FakeChatRepository(IChatRepository):
    def __init__(self) -> None:
        self.chats: dict[str, Chat] = {}
        self.mensajes: dict[str, Mensaje] = {}

    async def buscar_por_usuario_y_publicacion(self, respondedor_id, publicacion_id):
        c = next((c for c in self.chats.values()
                  if c.respondedor_id == respondedor_id and c.publicacion_id == publicacion_id), None)
        return copy.deepcopy(c) if c else None

    async def crear_con_primer_mensaje(self, chat, primer_mensaje):
        if await self.buscar_por_usuario_y_publicacion(chat.respondedor_id, chat.publicacion_id):
            raise Conflicto("chat duplicado", codigo="chat_existente")
        chat = copy.deepcopy(chat)
        chat.id = chat.id or nuevo_id()
        self.chats[chat.id] = chat
        mensaje = copy.deepcopy(primer_mensaje)
        mensaje.id, mensaje.chat_id = mensaje.id or nuevo_id(), chat.id
        self.mensajes[mensaje.id] = mensaje
        return chat.id

    async def eliminar_chat(self, chat_id):
        self.chats.pop(chat_id, None)
        propios = [m for m in self.mensajes.values() if m.chat_id == chat_id]
        for m in propios:
            del self.mensajes[m.id]
        return [m.imagen.referencia for m in propios if m.imagen]

    async def listar_activos_por_usuario(self, usuario_id, ahora):
        activos = [copy.deepcopy(c) for c in self.chats.values()
                   if usuario_id in c.participantes and c.activo(ahora)]
        return sorted(activos, key=lambda c: c.ultima_actividad, reverse=True)

    async def buscar_por_id(self, chat_id):
        c = self.chats.get(chat_id)
        return copy.deepcopy(c) if c else None

    async def listar_mensajes(self, chat_id, despues_de=None):
        lista = [copy.deepcopy(m) for m in self.mensajes.values()
                 if m.chat_id == chat_id and (despues_de is None or m.fecha_envio > despues_de)]
        return sorted(lista, key=lambda m: m.fecha_envio)

    async def buscar_mensaje(self, chat_id, mensaje_id):
        m = self.mensajes.get(mensaje_id)
        return copy.deepcopy(m) if m and m.chat_id == chat_id else None

    async def agregar_mensaje(self, mensaje, nueva_expiracion):
        c = self.chats.get(mensaje.chat_id)
        if not c or not c.activo(mensaje.fecha_envio):
            return None
        mensaje = copy.deepcopy(mensaje)
        mensaje.id = mensaje.id or nuevo_id()
        self.mensajes[mensaje.id] = mensaje
        c.ultima_actividad, c.fecha_expiracion = mensaje.fecha_envio, nueva_expiracion
        c.ultima_lectura[mensaje.emisor_id] = mensaje.fecha_envio
        return mensaje.id

    async def marcar_leido(self, chat_id, usuario_id, ahora):
        if chat_id in self.chats:
            self.chats[chat_id].ultima_lectura[usuario_id] = ahora

    async def eliminar_expirados(self, ahora):
        imagenes: list[str] = []
        expirados = [c for c in self.chats.values() if not c.activo(ahora)]
        for c in expirados:
            imagenes += await self.eliminar_chat(c.id)
        return len(expirados), imagenes


class FakeReportRepository(IReportRepository):
    def __init__(self) -> None:
        self.reportes: dict[str, Reporte] = {}

    async def crear(self, reporte):
        reporte = copy.deepcopy(reporte)
        reporte.id = reporte.id or nuevo_id()
        self.reportes[reporte.id] = reporte
        return reporte.id

    async def existe_reporte(self, reportante_id, tipo, objeto_id):
        return any(r.reportante_id == reportante_id and r.tipo_objeto is tipo and r.objeto_id == objeto_id
                   for r in self.reportes.values())

    async def eliminar_vencidos(self, ahora):
        vencidos = [r for r in self.reportes.values() if r.fecha_retencion_fin <= ahora]
        for r in vencidos:
            del self.reportes[r.id]
        return len(vencidos), [k for r in vencidos for k in r.contenido.snapshot_imagenes]


class FakeParameterRepository(IParameterRepository):
    def __init__(self) -> None:
        self.guardados: dict[ClaveParametro, ParametroSistema] = {}

    async def guardar(self, parametro):
        self.guardados[parametro.clave] = parametro


# --- Constructores de entidades para pruebas ------------------------------------------
def estudiante(correo="ana@unas.edu.pe", nickname="ana_07", estado=EstadoCuenta.ACTIVA,
               fecha=datetime(2026, 10, 1), password_hash="hash::1nimda1x", **kw) -> Estudiante:
    from datetime import timezone

    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return Estudiante(id=kw.pop("id", ""), correo_institucional=correo, password_hash=password_hash,
                      nickname=nickname, estado=estado, fecha_registro=fecha,
                      activacion=kw.pop("activacion", EnlaceUnUso()), **kw)


def imagen(formato: str = "PNG", tamano: tuple[int, int] = (8, 8)) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", tamano, "blue").save(buf, format=formato)
    return buf.getvalue()


__all__ = [
    "FakeAccountRepository", "FakePublicationRepository", "FakeChatRepository", "FakeReportRepository",
    "FakeParameterRepository", "FakeConfig", "FakePasswordHasher", "FakeEmailSender", "FakeImageStorage",
    "FakeClock", "SecureTokenService", "nuevo_id", "estudiante", "imagen", "TipoPublicacion", "TipoObjetoReportado",
    "EstadoChat",
]
