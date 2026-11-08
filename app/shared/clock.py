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


_reloj: IClock = SystemClock()


def get_clock() -> IClock:
    return _reloj
