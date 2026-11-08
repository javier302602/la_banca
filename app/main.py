"""Punto de entrada: crea la app FastAPI e incluye el router de cada slice y job."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.features.m01_acceso.cu01_registrar_cuenta.endpoint import router as cu01_registrar_cuenta
from app.features.m01_acceso.cu02_iniciar_sesion.endpoint import router as cu02_iniciar_sesion
from app.features.m01_acceso.cu03_cerrar_sesion.endpoint import router as cu03_cerrar_sesion
from app.features.m01_acceso.cu04_editar_nickname.endpoint import router as cu04_editar_nickname
from app.features.m01_acceso.cu16_consultar_terminos.endpoint import router as cu16_consultar_terminos
from app.features.m01_acceso.cu17_activar_cuenta.endpoint import router as cu17_activar_cuenta
from app.features.m01_acceso.cu18_recuperar_contrasena.endpoint import router as cu18_recuperar_contrasena
from app.features.m02_publicaciones.cu05_crear_publicacion.endpoint import router as cu05_crear_publicacion
from app.features.m02_publicaciones.cu06_ver_mis_publicaciones.endpoint import router as cu06_ver_mis_publicaciones
from app.features.m02_publicaciones.cu07_cerrar_publicacion.endpoint import router as cu07_cerrar_publicacion
from app.features.m03_feed.cu08_consultar_feed.endpoint import router as cu08_consultar_feed
from app.features.m03_feed.cu09_ver_detalle_publicacion.endpoint import router as cu09_ver_detalle_publicacion
from app.features.m04_chat.cu10_responder_publicacion.endpoint import router as cu10_responder_publicacion
from app.features.m04_chat.cu11_enviar_mensaje.endpoint import router as cu11_enviar_mensaje
from app.features.m04_chat.cu12_ver_mis_chats.endpoint import router as cu12_ver_mis_chats
from app.features.m05_reportes.cu13_reportar_publicacion.endpoint import router as cu13_reportar_publicacion
from app.features.m05_reportes.cu14_reportar_chat.endpoint import router as cu14_reportar_chat
from app.features.m06_configuracion.cu15_configurar_parametros.endpoint import router as cu15_configurar_parametros
from app.jobs.ea03_limpiar_chats_expirados.endpoint import router as ea03_limpiar_chats_expirados
from app.jobs.ea05_depurar_contenido_reportado.endpoint import router as ea05_depurar_contenido_reportado
from app.jobs.ea07_eliminar_cuentas_no_activadas.endpoint import router as ea07_eliminar_cuentas_no_activadas
from app.shared.db.mongo import asegurar_indices_una_vez
from app.shared.domain.errors import ErrorDominio

logging.basicConfig(level=logging.INFO)
RAIZ = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asegurar_indices_una_vez()
    yield


app = FastAPI(title="La Banca", version="1.0.0", lifespan=lifespan)


@app.exception_handler(ErrorDominio)
async def manejar_error_dominio(_: Request, error: ErrorDominio) -> JSONResponse:
    return JSONResponse({"detail": error.mensaje, "codigo": error.codigo, **error.extra}, status_code=error.status)


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def manejar_validacion(_: Request, error: RequestValidationError | ValidationError) -> JSONResponse:
    """422 con el mensaje del SRS (DTOs validados por FastAPI o construidos en el endpoint)."""
    inicio = 1 if isinstance(error, RequestValidationError) else 0
    errores = []
    for e in error.errors():
        mensaje = str(e.get("msg", "Dato inválido")).removeprefix("Value error, ")
        errores.append({"campo": ".".join(str(p) for p in e.get("loc", [])[inicio:]), "mensaje": mensaje})
    detalle = errores[0]["mensaje"] if errores else "Datos inválidos"
    return JSONResponse({"detail": detalle, "codigo": "validacion", "errores": errores}, status_code=422)


for router in [
    cu01_registrar_cuenta, cu02_iniciar_sesion, cu03_cerrar_sesion, cu04_editar_nickname,
    cu16_consultar_terminos, cu17_activar_cuenta, cu18_recuperar_contrasena,
    cu05_crear_publicacion, cu06_ver_mis_publicaciones, cu07_cerrar_publicacion,
    cu08_consultar_feed, cu09_ver_detalle_publicacion,
    cu10_responder_publicacion, cu11_enviar_mensaje, cu12_ver_mis_chats,
    cu13_reportar_publicacion, cu14_reportar_chat, cu15_configurar_parametros,
    ea03_limpiar_chats_expirados, ea05_depurar_contenido_reportado, ea07_eliminar_cuentas_no_activadas,
]:
    app.include_router(router)

app.mount("/static", StaticFiles(directory=RAIZ / "web" / "static"), name="static")
