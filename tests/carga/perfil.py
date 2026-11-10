"""Perfil de carga y límites de los RNF de rendimiento (SRS v1.9, RNF-REN-01 a RNF-REN-06, PA-26, PA-35).

Módulo puro (sin Locust ni red) para que pytest pueda verificarlo sin el monkey patching de gevent.
"""
from dataclasses import dataclass

USUARIOS = 100                 # RNF-REN-01: 100 usuarios con sesión activa operando a la vez
DURACION = "15m"               # RNF-REN-01: prueba de carga de 15 minutos
CUENTAS_REGISTRADAS = 10_000   # RNF-REN-06 / PA-35
PUBLICACIONES_ACTIVAS = 3_000  # RNF-REN-02 / PA-35

# (clase de usuario, peso sobre 10, segundos entre acciones) — criterio de RNF-REN-01
PERFIL = {
    "LectorFeed": (6, 30),     # 60 % consulta el feed cada 30 s (la mitad con filtro por tipo)
    "Conversador": (3, 20),    # 30 % intercambia un mensaje cada 20 s
    "Publicador": (1, 120),    # 10 % crea o cierra una publicación cada 2 min
}

# Nombres de las mediciones en Locust
FEED = "REN-02 feed: primer bloque"
FEED_FILTRO = "REN-02 feed: primer bloque con filtro"
ENTREGA_TEXTO = "REN-03 entrega de texto al otro participante"
ENTREGA_IMAGEN = "REN-04 imagen de 5 MB visible para el otro participante"
CORREO = "REN-05 correo en cola tras el registro"

ERROR_MAXIMO = 0.01              # RNF-REN-01: < 1 % de solicitudes con error
P95_FEED_S = 3.0                 # RNF-REN-02
P95_TEXTO_S = 2.0                # RNF-REN-03
P95_IMAGEN_S = 10.0              # RNF-REN-04 (red ≥ 10 Mbps)
P95_CORREO_S = 30.0              # RNF-REN-05
RED_MBPS = 10                    # RNF-REN-04: ambos clientes en una red de al menos 10 Mbps


def segundos_de_transferencia(bytes_: int, mbps: float = RED_MBPS) -> float:
    """Tiempo de transferir `bytes_` a `mbps` megabits por segundo."""
    return bytes_ * 8 / (mbps * 1_000_000)


@dataclass(frozen=True)
class Resultado:
    rnf: str
    metrica: str
    valor: float
    limite: float
    cumple: bool
    unidad: str = "s"


def evaluar(solicitudes: int, fallos: int, p95_ms: dict[str, float], cuentas: int, activas: int) -> list[Resultado]:
    """Compara las mediciones con los límites del SRS. `p95_ms` usa los nombres de este módulo."""
    tasa = fallos / solicitudes if solicitudes else 1.0
    feed = max(p95_ms[FEED], p95_ms[FEED_FILTRO]) / 1000
    texto = p95_ms[ENTREGA_TEXTO] / 1000
    resultados = [
        Resultado("RNF-REN-01", f"tasa de errores ({fallos}/{solicitudes})", round(tasa * 100, 3),
                  ERROR_MAXIMO * 100, tasa < ERROR_MAXIMO, "%"),
        Resultado("RNF-REN-02", "p95 primer bloque del feed (con y sin filtro)", round(feed, 3), P95_FEED_S,
                  feed <= P95_FEED_S),
        Resultado("RNF-REN-03", "p95 entrega de un mensaje de texto", round(texto, 3), P95_TEXTO_S,
                  texto <= P95_TEXTO_S),
    ]
    if ENTREGA_IMAGEN in p95_ms:
        imagen = p95_ms[ENTREGA_IMAGEN] / 1000
        resultados.append(Resultado("RNF-REN-04", "p95 imagen de 5 MB visible (incluye red de 10 Mbps)",
                                    round(imagen, 3), P95_IMAGEN_S, imagen <= P95_IMAGEN_S))
    if CORREO in p95_ms:
        correo = p95_ms[CORREO] / 1000
        resultados.append(Resultado("RNF-REN-05", "p95 registro → correo entregado al emisor", round(correo, 3),
                                    P95_CORREO_S, correo <= P95_CORREO_S))
    escala = cuentas >= CUENTAS_REGISTRADAS and activas >= PUBLICACIONES_ACTIVAS
    resultados.append(Resultado("RNF-REN-06", f"REN-02 y REN-03 con {cuentas} cuentas y {activas} activas",
                                float(cuentas), CUENTAS_REGISTRADAS,
                                escala and resultados[1].cumple and resultados[2].cumple, "cuentas"))
    return resultados
