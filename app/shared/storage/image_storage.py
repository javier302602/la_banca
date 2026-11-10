"""Implementaciones de ImageStorage (RF-CHT-09, RNF-PRI-04, RNF-SEG-04).

- `MemoryImageStorage`: en memoria del proceso, para desarrollo y pruebas.
- `S3ImageStorage`: Object Storage compatible con S3 (AWS S3, Cloudflare R2, MinIO…).
Se elige con IMAGE_STORAGE=memoria|s3.

Antes de guardar, toda imagen se decodifica y se vuelve a codificar con Pillow: así se descartan los
metadatos EXIF (incluida la ubicación GPS) y se rechaza un archivo que no se pueda decodificar aunque
su firma corresponda a un formato permitido.
"""
import asyncio
import io
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from app.shared.config.provider import variable
from app.shared.domain.contracts import ImageStorage
from app.shared.domain.errors import ErrorValidacion

_FORMATO_PIL = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
_EXTENSION = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
              # Documentos del chat (SRS v2.0): la clave conserva la extensión del tipo detectado por contenido
              "application/pdf": "pdf", "text/plain": "txt",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
              "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx"}
MAX_PIXELES = 40_000_000  # defensa ante «bombas de descompresión»


def recodificar_sin_metadatos(contenido: bytes, mime_type: str) -> bytes:
    """Decodifica, aplica la orientación EXIF y vuelve a codificar sin metadatos. ErrorValidacion si falla."""
    formato = _FORMATO_PIL.get(mime_type)
    if formato is None:
        raise ErrorValidacion("Formato de imagen no permitido. Usa JPG, PNG o WebP")
    try:
        with Image.open(io.BytesIO(contenido)) as original:
            if original.format != formato:
                raise ErrorValidacion("El contenido de la imagen no coincide con su formato")
            if original.width * original.height > MAX_PIXELES:
                raise ErrorValidacion("La imagen tiene dimensiones demasiado grandes")
            original.load()  # fuerza la decodificación completa: un archivo truncado falla aquí
            imagen = ImageOps.exif_transpose(original)
            if formato == "JPEG" and imagen.mode not in ("RGB", "L"):
                imagen = imagen.convert("RGB")
            limpia = Image.new(imagen.mode, imagen.size)
            limpia.paste(imagen)  # copia solo los píxeles: sin EXIF, XMP ni ICC
            if imagen.mode == "P" and imagen.getpalette():
                limpia.putpalette(imagen.getpalette())
            salida = io.BytesIO()
            opciones = {"quality": 90} if formato in ("JPEG", "WEBP") else {}
            limpia.save(salida, format=formato, **opciones)
            return salida.getvalue()
    except ErrorValidacion:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ErrorValidacion("La imagen está dañada o no se puede leer") from None


def foto_cuadrada(contenido: bytes, mime_type: str, lado: int) -> bytes:
    """Foto de perfil (cambio 2.2): valida y limpia como cualquier imagen, recorta al cuadrado central,
    la reduce a `lado` px como máximo y la guarda en WebP (sin EXIF, XMP ni ICC)."""
    limpia = recodificar_sin_metadatos(contenido, mime_type)
    with Image.open(io.BytesIO(limpia)) as imagen:
        imagen.load()
        if imagen.mode not in ("RGB", "RGBA"):
            imagen = imagen.convert("RGBA" if "A" in imagen.getbands() or imagen.mode == "P" else "RGB")
        corte = min(imagen.size)
        cuadrada = ImageOps.fit(imagen, (min(corte, lado),) * 2, method=Image.Resampling.LANCZOS)
        salida = io.BytesIO()
        cuadrada.save(salida, format="WEBP", quality=85)
        return salida.getvalue()


def _nueva_clave(prefijo: str, mime_type: str) -> str:
    return f"{prefijo}/{uuid.uuid4().hex}.{_EXTENSION.get(mime_type, 'bin')}"


def _mime_de_clave(clave: str) -> str:
    extension = clave.rsplit(".", 1)[-1]
    return next((m for m, e in _EXTENSION.items() if e == extension), "application/octet-stream")


class MemoryImageStorage(ImageStorage):
    bucket = "memoria"

    def __init__(self) -> None:
        self.objetos: dict[str, bytes] = {}

    async def guardar(self, imagen: bytes, mime_type: str, prefijo: str = "chats") -> str:
        return await self.guardar_procesado(recodificar_sin_metadatos(imagen, mime_type), mime_type, prefijo)

    async def guardar_procesado(self, datos: bytes, mime_type: str, prefijo: str) -> str:
        clave = _nueva_clave(prefijo, mime_type)
        self.objetos[clave] = datos
        return clave

    async def copiar_a_retencion(self, referencia: str) -> str:
        clave = _nueva_clave("reports", _mime_de_clave(referencia))
        self.objetos[clave] = self.objetos[referencia]
        return clave

    async def leer(self, referencia: str) -> bytes | None:
        return self.objetos.get(referencia)

    async def eliminar(self, referencia: str) -> None:
        self.objetos.pop(referencia, None)


class S3ImageStorage(ImageStorage):
    """boto3 es síncrono: cada llamada se ejecuta en un hilo para no bloquear el event loop."""

    def __init__(self, bucket: str, endpoint: str | None, access_key: str | None, secret_key: str | None,
                 region: str | None = None) -> None:
        import boto3

        self._bucket = self.bucket = bucket
        self._s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key, region_name=region)

    async def guardar(self, imagen: bytes, mime_type: str, prefijo: str = "chats") -> str:
        return await self.guardar_procesado(recodificar_sin_metadatos(imagen, mime_type), mime_type, prefijo)

    async def guardar_procesado(self, datos: bytes, mime_type: str, prefijo: str) -> str:
        clave = _nueva_clave(prefijo, mime_type)
        await asyncio.to_thread(self._s3.put_object, Bucket=self._bucket, Key=clave, Body=datos,
                                ContentType=mime_type)
        return clave

    async def copiar_a_retencion(self, referencia: str) -> str:
        clave = _nueva_clave("reports", _mime_de_clave(referencia))
        await asyncio.to_thread(self._s3.copy_object, Bucket=self._bucket, Key=clave,
                                CopySource={"Bucket": self._bucket, "Key": referencia})
        return clave

    async def leer(self, referencia: str) -> bytes | None:
        from botocore.exceptions import ClientError

        try:
            respuesta = await asyncio.to_thread(self._s3.get_object, Bucket=self._bucket, Key=referencia)
        except ClientError:
            return None
        return await asyncio.to_thread(respuesta["Body"].read)

    async def eliminar(self, referencia: str) -> None:
        await asyncio.to_thread(self._s3.delete_object, Bucket=self._bucket, Key=referencia)


_almacen: ImageStorage | None = None


def get_image_storage() -> ImageStorage:
    global _almacen
    if _almacen is None:
        if variable("IMAGE_STORAGE", "memoria") == "s3":
            bucket = variable("STORAGE_BUCKET")
            if not bucket:
                raise RuntimeError("Falta configurar STORAGE_BUCKET")
            _almacen = S3ImageStorage(bucket, variable("STORAGE_ENDPOINT"), variable("STORAGE_ACCESS_KEY"),
                                      variable("STORAGE_SECRET_KEY"), variable("STORAGE_REGION"))
        else:
            _almacen = MemoryImageStorage()
    return _almacen


def mime_de_referencia(referencia: str) -> str:
    return _mime_de_clave(referencia)


async def leer_imagen_subida(archivo, limite: int | None = None) -> bytes | None:
    """Lee un UploadFile de FastAPI sin cargar más de `limite` (5 MB por omisión) + 1 byte.
    None si no se adjuntó archivo."""
    from app.shared.domain.entities import TAMANO_MAX_IMAGEN

    if archivo is None or not getattr(archivo, "filename", ""):
        return None
    contenido = await archivo.read((limite or TAMANO_MAX_IMAGEN) + 1)
    return contenido or None
