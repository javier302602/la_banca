"""CU-23 — Videollamada aleatoria entre estudiantes. Caso de uso (handler).

Flujo (cada navegador tiene una `Conexion` con su estado: inactivo → esperando → en_llamada):
1. «buscar»: el estudiante entra a la cola de espera (en Mongo, para que funcione con varios workers).
2. Cada segundo, quien espera intenta emparejarse: primero se saca a sí mismo de la cola (si ya no estaba, es
   que otra persona lo tomó y el aviso llegará a su buzón) y luego toma a otra persona al azar. Así nunca hay
   dos emparejamientos para la misma persona.
3. Quien empareja crea la sala y avisa a la otra persona por su buzón. Quien empareja es el «iniciador»: crea
   la oferta WebRTC. Las señales (oferta, respuesta, candidatos ICE) y el chat de texto viajan por los buzones.
   El audio y el video van directo entre los navegadores: el servidor no los ve ni los graba.
4. «siguiente» cuelga y vuelve a buscar (sin repetir a las últimas personas); «colgar» termina.
Requisito: cuenta activa con sesión y con nombre y carrera en el perfil (la llamada no es anónima).
"""
import json
from dataclasses import dataclass, field

from app.shared.domain.contracts import IClock, IVideollamadaRepository
from app.shared.domain.entities import VIGENCIA_EN_COLA, VIGENCIA_SENAL, ParticipanteVideollamada
from app.shared.domain.reglas import normalizar_texto

LARGO_CHAT = 500
TAMANO_MAX_SENAL = 64 * 1024   # una oferta SDP ocupa unos pocos KB
RECORDAR_ULTIMAS = 5           # «Siguiente» no vuelve a emparejar con las últimas 5 personas


@dataclass
class Conexion:
    yo: ParticipanteVideollamada
    estado: str = "inactivo"            # inactivo | esperando | en_llamada
    sala_id: str | None = None
    pareja_id: str | None = None
    evitar: list[str] = field(default_factory=list)


def publico(p: ParticipanteVideollamada) -> dict:
    """Lo que ve la otra persona: nombre, carrera y nickname (nunca el correo)."""
    return {"nombre": p.nombre, "carrera": p.carrera, "nickname": p.nickname}


class VideollamadaHandler:
    def __init__(self, llamadas: IVideollamadaRepository, clock: IClock) -> None:
        self._llamadas = llamadas
        self._clock = clock

    async def conectar(self, estudiante_id: str) -> Conexion | None:
        """None si el perfil no tiene nombre y carrera."""
        yo = await self._llamadas.buscar_participante(estudiante_id)
        if yo is None or not yo.nombre or not yo.carrera:
            return None
        return Conexion(yo)

    # --- acciones del navegador -------------------------------------------------------------------------
    async def buscar(self, c: Conexion) -> list[dict]:
        respuestas = await self.colgar(c) if c.estado != "inactivo" else []
        await self._llamadas.entrar_a_la_cola(c.yo, c.evitar, self._clock.ahora() + VIGENCIA_EN_COLA)
        c.estado = "esperando"
        return respuestas + [{"tipo": "esperando"}]

    async def siguiente(self, c: Conexion) -> list[dict]:
        if c.pareja_id:
            c.evitar = ([c.pareja_id] + [e for e in c.evitar if e != c.pareja_id])[:RECORDAR_ULTIMAS]
        return await self.buscar(c)

    async def colgar(self, c: Conexion) -> list[dict]:
        if c.estado == "esperando":
            await self._llamadas.salir_de_la_cola(c.yo.estudiante_id)
        if c.estado == "en_llamada":
            await self._avisar(c.pareja_id, {"tipo": "colgo", "sala": c.sala_id})
            await self._llamadas.cerrar_sala(c.sala_id, self._clock.ahora())
        c.estado, c.sala_id, c.pareja_id = "inactivo", None, None
        return [{"tipo": "colgado"}]

    async def reenviar(self, c: Conexion, mensaje: dict) -> list[dict]:
        """Señal WebRTC o mensaje de chat para la otra persona de la llamada."""
        if c.estado != "en_llamada":
            return []
        if mensaje.get("tipo") == "senal":
            datos = mensaje.get("datos")
            if not isinstance(datos, dict) or len(json.dumps(datos)) > TAMANO_MAX_SENAL:
                return [{"tipo": "error", "mensaje": "Señal no válida"}]
            await self._avisar(c.pareja_id, {"tipo": "senal", "sala": c.sala_id, "datos": datos})
            return []
        texto = normalizar_texto(str(mensaje.get("texto") or ""))
        if not 1 <= len(texto) <= LARGO_CHAT:
            return [{"tipo": "error", "mensaje": f"El mensaje debe tener entre 1 y {LARGO_CHAT} caracteres"}]
        await self._avisar(c.pareja_id, {"tipo": "chat", "sala": c.sala_id, "texto": texto})
        return []

    # --- lo que hace el servidor solo ---------------------------------------------------------------------
    async def intentar_emparejar(self, c: Conexion) -> list[dict]:
        if c.estado != "esperando":
            return []
        ahora = self._clock.ahora()
        if not await self._llamadas.salir_de_la_cola(c.yo.estudiante_id):
            return []  # otra persona me tomó: el aviso «emparejado» llega a mi buzón
        pareja = await self._llamadas.tomar_al_azar(c.yo.estudiante_id, c.evitar, ahora)
        if pareja is None:
            await self._llamadas.entrar_a_la_cola(c.yo, c.evitar, ahora + VIGENCIA_EN_COLA)  # renueva mi lugar
            return []
        sala = await self._llamadas.crear_sala([c.yo.estudiante_id, pareja.estudiante_id], ahora)
        await self._avisar(pareja.estudiante_id, {"tipo": "emparejado", "sala": sala.id, "pareja": publico(c.yo),
                                                  "pareja_id": c.yo.estudiante_id, "iniciador": False})
        c.estado, c.sala_id, c.pareja_id = "en_llamada", sala.id, pareja.estudiante_id
        return [{"tipo": "emparejado", "sala": sala.id, "pareja": publico(pareja), "iniciador": True}]

    async def leer_buzon(self, c: Conexion) -> list[dict]:
        respuestas = []
        for m in await self._llamadas.recibir(c.yo.estudiante_id):
            if m["tipo"] == "emparejado":
                if c.estado != "esperando":  # ya colgué o estoy en otra llamada: se lo digo a quien me tomó
                    await self._avisar(m["pareja_id"], {"tipo": "colgo", "sala": m["sala"]})
                    continue
                c.estado, c.sala_id, c.pareja_id = "en_llamada", m["sala"], m["pareja_id"]
                respuestas.append({k: v for k, v in m.items() if k != "pareja_id"})
            elif m.get("sala") == c.sala_id and c.estado == "en_llamada":  # señales viejas de otra sala, no
                if m["tipo"] == "colgo":
                    c.estado, c.sala_id, c.pareja_id = "inactivo", None, None
                respuestas.append(m)
        return respuestas

    async def desconectar(self, c: Conexion) -> None:
        await self.colgar(c)

    async def _avisar(self, para: str, mensaje: dict) -> None:
        await self._llamadas.enviar(para, mensaje, self._clock.ahora() + VIGENCIA_SENAL)
