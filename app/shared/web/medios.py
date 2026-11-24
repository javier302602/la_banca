"""Respuestas de audio y video con soporte de «Range» (HTTP 206).

Safari/WebKit no reproduce <audio> ni <video> si el servidor no acepta pedidos por rangos de bytes. Los demás
navegadores también lo usan para adelantar la reproducción. Solo se atiende un rango («bytes=inicio-fin»).
"""
from fastapi import Request, Response


def respuesta_con_rango(request: Request, contenido: bytes, media_type: str, headers: dict[str, str]) -> Response:
    total = len(contenido)
    cabeceras = {**headers, "Accept-Ranges": "bytes"}
    rango = _leer_rango(request.headers.get("range"), total)
    if rango is None:
        return Response(contenido, media_type=media_type, headers=cabeceras)
    if rango == "invalido":
        return Response(status_code=416, headers={**cabeceras, "Content-Range": f"bytes */{total}"})
    inicio, fin = rango
    cabeceras["Content-Range"] = f"bytes {inicio}-{fin}/{total}"
    return Response(contenido[inicio:fin + 1], status_code=206, media_type=media_type, headers=cabeceras)


def _leer_rango(valor: str | None, total: int):
    """(inicio, fin) inclusivo; None si no hay rango (o no se entiende); "invalido" si está fuera del archivo."""
    if not valor or not valor.startswith("bytes=") or "," in valor:
        return None
    desde, _, hasta = valor.removeprefix("bytes=").strip().partition("-")
    try:
        if desde == "":                      # «bytes=-500»: los últimos 500 bytes
            inicio, fin = max(0, total - int(hasta)), total - 1
        else:
            inicio = int(desde)
            fin = min(int(hasta), total - 1) if hasta else total - 1
    except ValueError:
        return None
    if total == 0 or inicio >= total or inicio > fin:
        return "invalido"
    return inicio, fin
