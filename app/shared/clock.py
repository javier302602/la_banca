"""Reloj inyectable. Usar siempre en lugar de datetime.now() (RNF-MAN-02)."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.shared.domain.contracts import IClock

ZONA_SISTEMA = ZoneInfo("America/Lima")  # RN-34: hora del sistema (UTC−5)


def hora_hhmm(instante: datetime) -> str:
    """HH:MM de 24 horas en la hora del sistema (America/Lima), nunca la del dispositivo (RF-CHT-11, RN-34)."""
    if instante.tzinfo is None:  # MongoDB devuelve UTC; un valor ingenuo se interpreta como UTC
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(ZONA_SISTEMA).strftime("%H:%M")


class SystemClock(IClock):
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)


class FakeClock(IClock):
    """Reloj controlable para pruebas de plazos (24 h, 72 h, 15 min…)."""

    def __init__(self, inicio: datetime | None = None) -> None:
        self._actual = inicio or datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc)

    def ahora(self) -> datetime:
        return self._actual

    def avanzar(self, **delta) -> datetime:
        self._actual += timedelta(**delta)
        return self._actual


class RelojDePruebas(IClock):
    """RNF-MAN-02: hora del sistema más un desfase que se puede adelantar en un entorno de pruebas desplegado.

    Solo se usa con ENTORNO=pruebas (ver get_clock). El desfase vive en la memoria del proceso: el entorno de
    pruebas debe correr con un solo worker para que todas las solicitudes vean la misma hora.
    """

    def __init__(self) -> None:
        self.desfase = timedelta(0)

    def ahora(self) -> datetime:
        return datetime.now(timezone.utc) + self.desfase

    def avanzar(self, delta: timedelta) -> datetime:
        if delta < timedelta(0):
            raise ValueError("El reloj de pruebas solo avanza")
        self.desfase += delta
        return self.ahora()

    def reiniciar(self) -> None:
        self.desfase = timedelta(0)


_reloj: IClock = SystemClock()
_reloj_pruebas = RelojDePruebas()


def en_entorno_de_pruebas() -> bool:
    import os

    return (os.environ.get("ENTORNO") or "").strip().lower() == "pruebas"


def get_clock() -> IClock:
    """Reloj del sistema; con ENTORNO=pruebas, el reloj de pruebas adelantable (RNF-MAN-02)."""
    return _reloj_pruebas if en_entorno_de_pruebas() else _reloj


def reloj_de_pruebas() -> RelojDePruebas:
    return _reloj_pruebas
