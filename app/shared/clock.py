"""Reloj inyectable. Usar siempre en lugar de datetime.now() (RNF-MAN-02)."""
from datetime import datetime, timedelta, timezone

from app.shared.domain.contracts import IClock


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
