"""RNF-FIA-02: al arrancar, aplicar los plazos que vencieron mientras el servicio estuvo detenido.

La vigencia de publicaciones, chats, sesiones y enlaces ya se evalúa en cada consulta (DD-03), así que el acceso
se corta en cuanto el servicio vuelve. Lo que depende de los jobs es la eliminación física (EA-03 chats expirados,
EA-05 contenido reportado vencido, EA-07 cuentas no activadas). Para no esperar al siguiente cron (hasta 1 h),
se ejecutan una vez en segundo plano al iniciar la app. Son idempotentes: que corran también en otro worker o
en el cron no cambia el resultado.
"""
import asyncio
import logging

log = logging.getLogger("la_banca.arranque")


async def aplicar_plazos_vencidos() -> dict[str, dict[str, int]]:
    from app.jobs.ea03_limpiar_chats_expirados.handler import LimpiarChatsExpiradosHandler
    from app.jobs.ea03_limpiar_chats_expirados.repository import MongoLimpiarChatsRepository
    from app.jobs.ea05_depurar_contenido_reportado.handler import DepurarContenidoReportadoHandler
    from app.jobs.ea05_depurar_contenido_reportado.repository import MongoDepurarReportesRepository
    from app.jobs.ea07_eliminar_cuentas_no_activadas.handler import EliminarCuentasNoActivadasHandler
    from app.jobs.ea07_eliminar_cuentas_no_activadas.repository import MongoEliminarCuentasRepository
    from app.shared.clock import get_clock
    from app.shared.config.provider import variable
    from app.shared.db.mongo import base_de_datos
    from app.shared.storage.image_storage import get_image_storage

    if not variable("MONGO_URI"):
        return {}
    try:
        db, imagenes, reloj = base_de_datos(), get_image_storage(), get_clock()
    except RuntimeError:
        log.exception("No se pudieron aplicar los plazos vencidos al arrancar")
        return {}
    trabajos = {
        "ea03": LimpiarChatsExpiradosHandler(MongoLimpiarChatsRepository(db), imagenes, reloj),
        "ea05": DepurarContenidoReportadoHandler(MongoDepurarReportesRepository(db), imagenes, reloj),
        "ea07": EliminarCuentasNoActivadasHandler(MongoEliminarCuentasRepository(db), reloj),
    }
    resultados: dict[str, dict[str, int]] = {}
    for nombre, trabajo in trabajos.items():
        try:  # un fallo de uno no impide los demás; el cron los reintentará
            resultados[nombre] = await trabajo.handle()
        except Exception:
            log.exception("No se pudo ejecutar %s al arrancar", nombre)
    log.info("Plazos vencidos aplicados al arrancar: %s", resultados)
    return resultados


def programar_al_arrancar() -> asyncio.Task:
    """Lanza la tarea sin retrasar el arranque; se guarda la referencia para que no la recoja el GC."""
    tarea = asyncio.create_task(aplicar_plazos_vencidos(), name="aplicar-plazos-vencidos")
    _tareas.add(tarea)
    tarea.add_done_callback(_tareas.discard)
    return tarea


_tareas: set[asyncio.Task] = set()
