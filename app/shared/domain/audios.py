"""Audios y música adjuntos en el chat (Fase 3).

Formatos: MP3, WAV, OGG, M4A, AAC y FLAC. Como los documentos, el tipo se decide por el **contenido** (la firma
del archivo), nunca por la extensión ni por el Content-Type que envía el navegador. El tamaño máximo se lee de
.env (AUDIO_MAX_MB) en el endpoint y llega aquí como parámetro.

Se guardan como un documento más del mensaje (documentAttachment con tipo mp3, wav…), así reutilizan la descarga,
la limpieza al expirar el chat (EA-03) y la copia de retención al reportar (CU-14).
"""
from dataclasses import dataclass

from app.shared.domain.documentos import nombre_seguro

MIME_AUDIO = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "flac": "audio/flac",
}
TIPOS_AUDIO = tuple(MIME_AUDIO)
# Marcas «ftyp» de un MP4 de solo audio (iPhone: M4A; grabadoras Android: mp42/isom)
_MARCAS_M4A = (b"M4A ", b"M4B ", b"mp42", b"mp41", b"isom", b"iso2")

MSG_VACIO = "El audio está vacío"
MSG_FORMATO = "Formato de audio no permitido. Usa MP3, WAV, OGG, M4A, AAC o FLAC"


@dataclass(frozen=True)
class AudioValidado:
    tipo: str        # mp3 | wav | ogg | m4a | aac | flac
    mime_type: str
    nombre: str      # nombre saneado, con la extensión del tipo detectado


def detectar_tipo_audio(contenido: bytes) -> str | None:
    """Devuelve el tipo de audio por su firma, o None si no es un audio admitido."""
    cabecera = contenido[:12]
    if cabecera.startswith(b"ID3"):
        return "mp3"
    if cabecera.startswith(b"RIFF") and cabecera[8:12] == b"WAVE":
        return "wav"
    if cabecera.startswith(b"OggS"):
        return "ogg"
    if cabecera.startswith(b"fLaC"):
        return "flac"
    if cabecera[4:8] == b"ftyp" and cabecera[8:12] in _MARCAS_M4A:
        return "m4a"
    if cabecera.startswith(b"ADIF"):
        return "aac"
    if len(cabecera) >= 2 and cabecera[0] == 0xFF:
        segundo = cabecera[1]
        if segundo & 0xF6 == 0xF0:                         # sincronía ADTS: AAC «crudo»
            return "aac"
        if segundo & 0xE0 == 0xE0 and segundo & 0x06:     # sincronía de trama MPEG con capa 1–3: MP3 sin ID3
            return "mp3"
    return None


def validar_audio(contenido: bytes, nombre_original: str | None, tamano_max: int) -> AudioValidado:
    """Valida tipo y tamaño; lanza ValueError con el motivo en español."""
    if not contenido:
        raise ValueError(MSG_VACIO)
    if len(contenido) > tamano_max:
        raise ValueError(f"El audio supera el tamaño máximo de {tamano_max // (1024 * 1024)} MB")
    tipo = detectar_tipo_audio(contenido)
    if tipo is None:
        raise ValueError(MSG_FORMATO)
    return AudioValidado(tipo, MIME_AUDIO[tipo], nombre_seguro(nombre_original, tipo))
