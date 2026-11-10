"""Documentos adjuntos en el chat (SRS v2.0, cambio 4.4).

Se aceptan PDF, DOCX, XLSX, PPTX y TXT de hasta 10 MB. El tipo se decide por el **contenido**, nunca por la
extensión ni por el Content-Type que envía el navegador:

- PDF: empieza con «%PDF-».
- DOCX/XLSX/PPTX (Office Open XML): ZIP con `[Content_Types].xml` y la parte principal del formato
  (`word/document.xml`, `xl/workbook.xml` o `ppt/presentation.xml`). Se rechaza si trae macros
  (`vbaProject.bin` o un tipo de contenido «macroEnabled»: .docm, .xlsm, .pptm).
- TXT: UTF-8 válido, sin bytes nulos ni caracteres de control fuera de tabulador y saltos de línea.

Se rechazan los ejecutables (PE «MZ», ELF, Mach-O, scripts con «#!») aunque se renombren, y los documentos
de Office antiguos (OLE: .doc, .xls, .ppt), que pueden llevar macros.
"""
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass

TAMANO_MAX_DOCUMENTO = 10 * 1024 * 1024  # 10 485 760 bytes
MAX_ENTRADAS_ZIP = 5_000
MAX_DESCOMPRIMIDO_ZIP = 300 * 1024 * 1024  # defensa ante «bombas zip» (solo se lee el tamaño declarado)
LARGO_MAX_NOMBRE = 100

MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
}
PARTE_PRINCIPAL = {"word/document.xml": "docx", "xl/workbook.xml": "xlsx", "ppt/presentation.xml": "pptx"}

MSG_VACIO = "El documento está vacío"
MSG_GRANDE = "El documento supera el tamaño máximo de 10 MB"
MSG_FORMATO = "Formato de documento no permitido. Usa PDF, DOCX, XLSX, PPTX o TXT"
MSG_EJECUTABLE = "No se permiten archivos ejecutables"
MSG_MACROS = "No se permiten documentos de Office con macros (.docm, .xlsm, .pptm)"
MSG_DANADO = "El documento está dañado o no se puede leer"

_EJECUTABLES = (b"MZ", b"\x7fELF", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
                b"\xca\xfe\xba\xbe", b"#!")
_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_CONTROL_TXT = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class DocumentoValidado:
    tipo: str        # pdf | docx | xlsx | pptx | txt
    mime_type: str
    nombre: str      # nombre saneado, con la extensión del tipo detectado


def detectar_tipo(contenido: bytes) -> str:
    """Devuelve pdf|docx|xlsx|pptx|txt o lanza ValueError con el motivo en español."""
    if not contenido:
        raise ValueError(MSG_VACIO)
    if len(contenido) > TAMANO_MAX_DOCUMENTO:
        raise ValueError(MSG_GRANDE)
    if contenido.startswith(_EJECUTABLES):
        raise ValueError(MSG_EJECUTABLE)
    if contenido.startswith(b"%PDF-"):
        return "pdf"
    if contenido.startswith(b"PK\x03\x04"):
        return _tipo_office(contenido)
    if contenido.startswith(_OLE):
        raise ValueError(MSG_FORMATO)
    return _tipo_texto(contenido)


def _tipo_office(contenido: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as zf:
            entradas = zf.infolist()
            if len(entradas) > MAX_ENTRADAS_ZIP or sum(e.file_size for e in entradas) > MAX_DESCOMPRIMIDO_ZIP:
                raise ValueError(MSG_DANADO)
            nombres = {e.filename for e in entradas}
            if "[Content_Types].xml" not in nombres:
                raise ValueError(MSG_FORMATO)
            if any(n.lower().endswith("vbaproject.bin") or n.lower().endswith("vbadata.xml") for n in nombres):
                raise ValueError(MSG_MACROS)
            with zf.open("[Content_Types].xml") as tipos:
                declarados = tipos.read(1024 * 1024).decode("utf-8", errors="replace").lower()
    except zipfile.BadZipFile:
        raise ValueError(MSG_DANADO) from None
    except (RuntimeError, NotImplementedError, OSError, EOFError):  # cifrado, compresión no soportada…
        raise ValueError(MSG_DANADO) from None
    if "macroenabled" in declarados or "vbaproject" in declarados:
        raise ValueError(MSG_MACROS)
    tipos = {PARTE_PRINCIPAL[n] for n in PARTE_PRINCIPAL if n in nombres}
    if len(tipos) != 1:
        raise ValueError(MSG_FORMATO)
    return tipos.pop()


def _tipo_texto(contenido: bytes) -> str:
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError(MSG_FORMATO) from None
    if _CONTROL_TXT.search(texto):
        raise ValueError(MSG_FORMATO)
    return "txt"


def nombre_seguro(original: str | None, tipo: str) -> str:
    """Nombre para mostrar y descargar: sin rutas ni caracteres de control, con la extensión del tipo real."""
    base = (original or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = unicodedata.normalize("NFC", base)
    base = "".join(c for c in base if unicodedata.category(c)[0] != "C").strip().strip(".")
    if "." in base:
        base = base.rsplit(".", 1)[0]
    base = base.strip() or "documento"
    return f"{base[:LARGO_MAX_NOMBRE - len(tipo) - 1]}.{tipo}"


def validar_documento(contenido: bytes, nombre_original: str | None) -> DocumentoValidado:
    tipo = detectar_tipo(contenido)
    return DocumentoValidado(tipo, MIME[tipo], nombre_seguro(nombre_original, tipo))
