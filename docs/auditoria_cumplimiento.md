# Auditoría de cumplimiento — La Banca

**Fecha:** 10 de noviembre de 2026 · **Rama auditada:** `correcciones-auditoria` (fusionada en `main`) · **Referencias:** SRS v1.9 (`docs/La_Banca_Especificacion_de_Requisitos_2026_v1_9.docx`) y Entregable 2 v2.0 corregido (`docs/Entregable_2_v2_Corregido.docx`).

Tercera versión. Historial: la auditoría inicial (sobre `1621607`) dio 124/136 RF, 44/50 RN y 15/38 RNF en OK; la segunda, 136/136, 50/50 y 18/38. Esta versión refleja la segunda tanda de correcciones (usabilidad, compatibilidad, carga, robustez y respaldos).

## 1. Resumen

| Conjunto | Total | OK | PARCIAL | FALTA |
|---|---|---|---|---|
| Requisitos funcionales (RF) | 136 | 136 | 0 | 0 |
| Reglas de negocio (RN) | 50 | 50 | 0 | 0 |
| Requisitos no funcionales (RNF) | 38 | 34 | 3 | 1 |

**Pruebas:**
- **Unitarias:** 297 pasan (`pytest`).
- **e2e:** 36 pasan y 2 se omiten con motivo (`pytest -m e2e`), contra MongoDB 7 en Docker como replica set `rs0`.
- **Navegador:** Playwright en Chromium, Firefox y WebKit, con Pixel 7 e iPhone 14 emulados.
- **Carga:** Locust, 100 usuarios durante 15 min (sección 6).

### Qué depende del despliegue o del grupo

| RNF / RN | Depende de | Qué falta |
|---|---|---|
| RNF-DIS-01 (FALTA) | Despliegue | Monitor externo que consulte la página de inicio cada minuto y mida la disponibilidad mensual. |
| RNF-SEG-03 (PARCIAL) | Despliegue | Comprobar contra el dominio publicado que se rechaza TLS 1.0/1.1 (la app ya redirige a HTTPS y envía HSTS). |
| RNF-REN-01 a REN-06 (OK en local) | Despliegue | Repetir `tests/carga/ejecutar_carga.py` contra Vercel + Atlas, con el SMTP y el Object Storage reales. |
| RNF-PRI-02 (PARCIAL) | Grupo y despliegue | Crear los secrets `MONGO_URI` y `BACKUP_PASSPHRASE` para activar el respaldo diario; si se usan snapshots de Atlas, fijar su retención en ≤ 7 días. |
| RNF-COM-01 (PARCIAL) | Grupo | Probar en las dos últimas versiones de Chrome, Firefox y Edge, y en Chrome Android y Safari iOS reales. |
| RN-31, RNF-LEG-01/02/03 (OK) | Grupo | Texto legal aprobado y los valores de `TERMINOS_VERSION`, `TERMINOS_FECHA` y `CANAL_ARCO`. |
| RF-CFG-01 (OK) | Grupo | El SRS deja el dominio institucional «pendiente de decisión»: definir `DOMINIO_INSTITUCIONAL`. |

### Correcciones de esta versión

| Commit | Cambio | Requisitos |
|---|---|---|
| `dcf8de8` | README: variables de la política en el despliegue | RN-31 |
| `4d13b49` | 404 y 405 en español (página HTML o JSON) | RNF-USA-05 |
| `b064ebc` | Corrige un error de sintaxis en chat.js introducido en `f6a3b3f` (el chat dejaba de funcionar); test `node --check` de todo el JS | RF-CHT-* |
| `50d19ec` | Errores junto al campo, contraseñas vaciadas tras un error, etiquetas visibles; pruebas en navegador | RNF-USA-03/06/07 |
| `921075a` | 360 px, axe-core y teclado; contraste de los botones outline | RNF-USA-02/04/08 |
| `23e4241` | Chromium, Firefox y WebKit; flujos principales en escritorio y móvil emulado | RNF-COM-01 |
| `01f8636` | Prueba de carga con Locust y resultados | RNF-REN-01 a 06 |
| `7e2af77` | Plazos vencidos al arrancar, HTTPS/HSTS, registros sin contenido de chats, reloj de pruebas; EA-07 tolera la falta del índice | RNF-FIA-02, SEG-03, PRI-05, MAN-02 |
| `3f99195` | Respaldo diario cifrado como artifact de 7 días | RNF-PRI-02 |

### Observaciones

- **Latencia en el arranque de la carga:** los máximos de 3,5 a 8,5 s coinciden con la rampa de inicio, cuando 130 sesiones se inician casi a la vez. `bcrypt` verifica la contraseña de forma síncrona dentro de un endpoint async y bloquea el event loop del worker mientras tanto. Los p95 cumplen, pero conviene moverlo a un hilo (`asyncio.to_thread`), igual que el recodificado de imágenes con Pillow.
- **Imágenes en memoria:** con `IMAGE_STORAGE=memoria` y varios workers, una imagen guardada por un worker no la ve otro. En producción se exige `s3` (`verificar_entorno`). La medición de RNF-REN-04 usó un solo worker.

### Criterios de estado

- **OK:** el criterio se verificó con al menos una prueba automatizada (los RNF de carga, con la prueba que describe el SRS, en local).
- **PARCIAL:** (a) implementación incompleta o que se desvía del SRS, o (b) una parte del criterio no se puede verificar desde el repositorio. La columna *Observación* lo indica.
- **FALTA:** no implementado.

### Leyenda de rutas

| Abreviatura | Ruta completa |
|---|---|
| `cuNN/archivo.py` | `app/features/<módulo>/cuNN_<nombre>/archivo.py` (p. ej. `cu01/` = `app/features/m01_acceso/cu01_registrar_cuenta/`) |
| `eaNN/` | `app/jobs/eaNN_<nombre>/` |
| `reglas.py`, `entities.py` | `app/shared/domain/` |
| `mongo.py`, `mapeo.py` | `app/shared/db/` |
| `security/`, `config/`, `email/`, `storage/`, `clock.py` | `app/shared/…` |
| `*.html` | `web/templates/<módulo>/` · `*.js` → `web/static/js/` |
| `T:cuNN::test_x` | `tests/features/<módulo>/cuNN_<nombre>/test_handler.py::test_x` |
| `T:eaNN::test_x` | `tests/jobs/eaNN_<nombre>/test_handler.py::test_x` |
| `T:shared::` · `T:tx::` · `T:rob::` | `tests/shared/test_base_compartida.py` · `test_transacciones.py` · `test_robustez.py` |
| `T:web::` · `T:webjs::` · `T:webval::` · `T:webhttp::` | `tests/web/test_paginas.py` · `test_frontend_js.py` · `test_validacion_espanol.py` · `test_errores_http.py` |
| `T:conf::` | `tests/features/m05_reportes/test_confidencialidad.py` |
| `T:scripts::` · `T:wf::` | `tests/scripts/test_respaldo_mongodb.py` · `tests/scripts/test_workflow_respaldo.py` |
| `T:nav-form::` · `T:nav-a11y::` · `T:nav-compat::` | `tests/e2e/navegador/test_formularios.py` · `test_accesibilidad.py` · `test_compatibilidad.py` (Playwright) |
| `T:e2e::` · `T:e2e-cupo::` · `T:e2e-rob::` | `tests/e2e/test_flujo_completo.py` · `test_cupo_concurrente.py` · `test_robustez.py` (requieren MongoDB con replica set) |

## 2. Requisitos funcionales (136)

### AUT — Acceso y cuenta (49)

| RF | Nombre | Prio. | Implementación | Test que lo verifica | Estado | Observación |
|---|---|---|---|---|---|---|
| RF-AUT-01 | Registrar cuenta | E | cu01/handler.py, cu01/request.py | T:cu01::test_registro_crea_cuenta_pendiente_y_envia_enlace; T:e2e::test_flujo_completo | **OK** |  |
| RF-AUT-02 | Rechazar correo de otro dominio | E | cu01/handler.py; reglas.py `correo_del_dominio` | T:cu01::test_rechaza_otro_dominio_y_subdominio; T:shared::test_normalizacion_y_dominio | **OK** |  |
| RF-AUT-03 | Rechazar correo ya registrado | E | cu01/handler.py | T:cu01::test_rechaza_correo_activo_o_pendiente | **OK** |  |
| RF-AUT-04 | Exigir nickname en el registro | E | reglas.py `validar_nickname` | T:cu01::test_validaciones_del_dto; T:shared::test_nickname_vacio_es_obligatorio | **OK** |  |
| RF-AUT-05 | Validar formato del nickname | E | reglas.py `validar_nickname` | T:shared::test_nickname_valido / test_nickname_invalido; T:cu04::test_valida_formato | **OK** |  |
| RF-AUT-06 | Garantizar unicidad del nickname | E | cu01/handler.py, cu01/repository.py; mongo.py `uq_accounts_nickname` (colación) | T:cu01::test_nickname_ocupado_sin_distinguir_mayusculas; T:e2e::test_flujo_completo | **OK** |  |
| RF-AUT-07 | Vincular el correo a la cuenta | E | reglas.py `normalizar_correo`; cu01/request.py | T:cu01::test_registro_crea_cuenta_pendiente_y_envia_enlace | **OK** |  |
| RF-AUT-08 | Iniciar sesión | E | cu02/handler.py; acceso.js (redirige a /feed) | T:cu02::test_inicio_exitoso_crea_sesion_de_12_horas | **OK** |  |
| RF-AUT-09 | Rechazar credenciales inválidas | E | cu02/handler.py (hash señuelo) | T:cu02::test_mismo_mensaje_para_correo_o_clave_incorrectos | **OK** |  |
| RF-AUT-10 | Cerrar sesión manualmente | E | cu03/handler.py | T:cu03::test_cierra_solo_la_sesion_actual | **OK** |  |
| RF-AUT-11 | Cerrar sesión por inactividad | E | security/session.py `ValidadorSesion` | T:shared::test_sesion_expirada_queda_invalidada | **OK** | Se evalúa en la siguiente solicitud (DD-03). |
| RF-AUT-12 | Reiniciar el conteo de inactividad de la sesión | E | security/session.py | T:shared::test_sesion_valida_reinicia_conteo_por_interaccion | **OK** |  |
| RF-AUT-13 | Editar nickname | E | cu04/handler.py | T:cu04::test_cambia_nickname_y_libera_el_anterior | **OK** |  |
| RF-AUT-14 | Validar formato de la contraseña | E | reglas.py `validar_contrasena` | T:shared::test_politica_contrasena | **OK** |  |
| RF-AUT-15 | Confirmar la contraseña | E | reglas.py `validar_confirmacion` | T:shared::test_confirmacion; T:cu01::test_validaciones_del_dto | **OK** |  |
| RF-AUT-16 | Exigir aceptación de términos y privacidad | E | cu01/request.py; registro.html | T:cu01::test_validaciones_del_dto; T:web::test_registro_casilla_desmarcada | **OK** |  |
| RF-AUT-17 | Registrar la aceptación | E | cu01/handler.py `AceptacionTerminos`; mapeo.py `termsAcceptance` | T:cu01::test_registro_crea_cuenta_pendiente_y_envia_enlace | **OK** | Si `TERMINOS_VERSION` está vacío se registra la versión «pendiente». |
| RF-AUT-18 | Consultar términos y política de privacidad sin sesión | E | cu16/*; login.html, registro.html, base.html (pie) | T:cu16::test_devuelve_version_fecha_y_texto, test_texto_incluye_datos_tratados_y_api_sin_sesion; T:web::test_paginas_publicas | **OK** |  |
| RF-AUT-19 | Bloquear tras intentos fallidos | E | cu02/handler.py; entities.py `IntentoAcceso.registrar_fallo` (ventana móvil con `failedAt`) | T:cu02::test_ventana_movil_de_15_minutos, test_bloqueo_tras_5_fallos_y_desbloqueo_ea06, test_bloqueo_aplica_a_correos_sin_cuenta, test_intento_antiguo_sin_failed_at_se_reconstruye | **OK** | Corregido: ventana móvil de 15 min (commit `0147a2a`). |
| RF-AUT-20 | Permitir sesiones simultáneas | E | cu02/handler.py, cu03/handler.py | T:cu02::test_sesiones_simultaneas; T:cu03::test_cierra_solo_la_sesion_actual | **OK** |  |
| RF-AUT-21 | Informar el bloqueo temporal | E | cu02/handler.py | T:cu02::test_bloqueo_tras_5_fallos_y_desbloqueo_ea06 | **OK** |  |
| RF-AUT-22 | Reiniciar el contador de intentos fallidos | E | cu02/handler.py | T:cu02::test_exito_reinicia_contador | **OK** |  |
| RF-AUT-23 | Informar el cierre por inactividad | D | security/session.py; plantillas.py `redirigir_a_login`; login.html | T:shared::test_actualizacion_automatica_no_reinicia_conteo; T:web::test_redireccion_por_inactividad_muestra_aviso | **OK** |  |
| RF-AUT-24 | Consultar términos y política de privacidad con sesión | E | cu16/*; editar_nickname.html (enlace desde el perfil) | T:cu16::test_devuelve_version_fecha_y_texto | **OK** | El enlace del perfil no tiene test propio; la página es la misma de RF-AUT-18. |
| RF-AUT-25 | No reiniciar el conteo por actualizaciones automáticas | E | security/session.py (cabecera `X-Actualizacion-Automatica`); app.js | T:shared::test_actualizacion_automatica_no_reinicia_conteo | **OK** |  |
| RF-AUT-26 | Mostrar el nuevo nickname | E | cu04/repository.py (propaga a publications, chats y messages) | T:e2e::test_flujo_completo («nickname propagado») | **OK** | Solo lo verifica la prueba e2e (ejecutada en esta auditoría). |
| RF-AUT-27 | Liberar el nickname anterior | E | cu04/repository.py | T:cu04::test_cambia_nickname_y_libera_el_anterior | **OK** |  |
| RF-AUT-28 | Enviar el correo de activación | E | cu01/handler.py; email/sender.py | T:shared::test_correo_de_activacion_incluye_enlace_y_nickname; T:cu01::test_registro_crea_cuenta_pendiente_y_envia_enlace | **OK** |  |
| RF-AUT-29 | Activar la cuenta con el enlace | E | cu17/handler.py, cu17/repository.py | T:cu17::test_activa_con_enlace_vigente_una_sola_vez | **OK** |  |
| RF-AUT-30 | Impedir el acceso con una cuenta no activada | E | cu02/handler.py | T:cu02::test_cuenta_pendiente_no_obtiene_sesion | **OK** |  |
| RF-AUT-31 | Rechazar un enlace de activación no válido | E | cu17/handler.py; acceso.js (ofrece nuevo enlace) | T:cu17::test_activa_con_enlace_vigente_una_sola_vez, test_rechaza_enlace_vencido_o_inexistente | **OK** |  |
| RF-AUT-32 | Solicitar un nuevo enlace de activación | E | cu17/handler.py `reenviar` | T:cu17::test_reenvio_invalida_enlace_anterior | **OK** |  |
| RF-AUT-33 | No exceder el límite de enlaces de activación | E | cu17/handler.py `reenviar` (ventana móvil con `sentAt`) | T:cu17::test_reenvio_limite_5_en_24h_con_mismo_mensaje | **OK** |  |
| RF-AUT-34 | Eliminar las cuentas no activadas | E | ea07/* (consulta por `ix_accounts_activation_exp`); entities.py `pendiente_vencida`; cu01 y cu17 al consultar | T:ea07::test_elimina_pendientes_con_72_horas_y_respeta_activas, test_repositorio_consulta_por_ix_accounts_activation_exp; T:cu01::test_pendiente_vencida_libera_correo_y_nickname; T:e2e::test_feed_paginado_y_jobs | **OK** |  |
| RF-AUT-35 | Solicitar la recuperación de la contraseña | E | cu18/handler.py `handle` | T:cu18::test_respuesta_uniforme_sin_cuenta_o_cuenta_pendiente | **OK** |  |
| RF-AUT-36 | Enviar el correo de recuperación | E | cu18/handler.py `handle` | T:cu18::test_flujo_completo_cierra_todas_las_sesiones | **OK** |  |
| RF-AUT-37 | Establecer una nueva contraseña | E | cu18/handler.py `restablecer`; cu18/request.py | T:cu18::test_valida_nueva_contrasena, test_flujo_completo_cierra_todas_las_sesiones | **OK** |  |
| RF-AUT-38 | Rechazar un enlace de recuperación no válido | E | cu18/handler.py; acceso.js | T:cu18::test_flujo_completo_cierra_todas_las_sesiones, test_enlace_vence_a_los_30_minutos | **OK** |  |
| RF-AUT-39 | Cerrar las sesiones al recuperar la contraseña | E | cu18/repository.py `cerrar_sesiones_de` | T:cu18::test_flujo_completo_cierra_todas_las_sesiones; T:e2e::test_flujo_completo | **OK** |  |
| RF-AUT-41 | Crear la cuenta pendiente de activación | E | cu01/handler.py | T:cu01::test_registro_crea_cuenta_pendiente_y_envia_enlace | **OK** |  |
| RF-AUT-42 | Pedir que revise su correo | E | cu01/handler.py | T:cu01::test_registro_crea_cuenta_pendiente_y_envia_enlace | **OK** |  |
| RF-AUT-43 | Rechazar el registro con un correo pendiente de activación | E | cu01/handler.py; acceso.js (ofrece nuevo enlace) | T:cu01::test_rechaza_correo_activo_o_pendiente | **OK** |  |
| RF-AUT-44 | Mostrar la confirmación de activación | E | cu17/handler.py | T:cu17::test_activa_con_enlace_vigente_una_sola_vez | **OK** |  |
| RF-AUT-45 | Ofrecer continuar al inicio de sesión | E | activar_cuenta.html (`#continuar` → /login); acceso.js | T:webjs::test_activacion_ofrece_continuar_al_inicio_de_sesion | **OK** |  |
| RF-AUT-46 | Invalidar el enlace de activación anterior | E | cu17/handler.py `reenviar` | T:cu17::test_reenvio_invalida_enlace_anterior | **OK** |  |
| RF-AUT-47 | Responder igual a la solicitud de un nuevo enlace de activación | E | cu17/handler.py `reenviar` | T:cu17::test_reenvio_misma_respuesta_si_no_hay_cuenta_pendiente | **OK** |  |
| RF-AUT-48 | Confirmar la actualización de la contraseña | E | cu18/handler.py `restablecer` | T:cu18::test_flujo_completo_cierra_todas_las_sesiones | **OK** |  |
| RF-AUT-49 | No exceder el límite de enlaces de recuperación | E | cu18/handler.py `handle` | T:cu18::test_nuevo_enlace_invalida_el_anterior_y_limite_5 | **OK** |  |
| RF-AUT-50 | Invalidar el enlace de recuperación anterior | E | cu18/handler.py, cu18/repository.py | T:cu18::test_nuevo_enlace_invalida_el_anterior_y_limite_5 | **OK** |  |

### PUB — Publicaciones (16)

| RF | Nombre | Prio. | Implementación | Test que lo verifica | Estado | Observación |
|---|---|---|---|---|---|---|
| RF-PUB-01 | Crear publicación | E | cu05/handler.py | T:cu05::test_crea_con_duracion_fija_de_24_horas; T:e2e::test_flujo_completo | **OK** |  |
| RF-PUB-02 | Exigir tipo de publicación | E | cu05/request.py (enum sin valor por defecto); crear_publicacion.html | T:web::test_crear_publicacion_sin_duracion_ni_tipo_preseleccionado; T:cu05::test_validaciones; T:webval::test_errores_de_validacion_en_espanol | **OK** |  |
| RF-PUB-03 | Validar título | E | cu05/request.py; reglas.py `validar_longitud` | T:cu05::test_validaciones, test_limites_exactos_aceptados | **OK** |  |
| RF-PUB-04 | Validar descripción | E | cu05/request.py; reglas.py `validar_longitud` | T:cu05::test_validaciones, test_limites_exactos_aceptados | **OK** |  |
| RF-PUB-05 | Aplicar la duración fija de la publicación | E | cu05/handler.py `DURACION_PUBLICACION` | T:cu05::test_crea_con_duracion_fija_de_24_horas | **OK** |  |
| RF-PUB-06 | Limitar publicaciones activas | E | cu05/handler.py, cu05/repository.py (transacción) | T:cu05::test_limite_de_activas_configurable; T:e2e-cupo::test_creaciones_simultaneas_respetan_el_maximo | **OK** |  |
| RF-PUB-07 | Registrar vencimiento | E | cu05/handler.py | T:cu05::test_crea_con_duracion_fija_de_24_horas | **OK** |  |
| RF-PUB-08 | Cerrar publicación manualmente | E | cu07/*; publicaciones.js (`confirm`) | T:cu07::test_autor_cierra_y_no_puede_reactivar, test_solo_el_autor | **OK** | El texto de confirmación solo está en el JS y no tiene test. |
| RF-PUB-09 | Expirar publicación automáticamente | E | entities.py `Publicacion.activa`; filtros `expiresAt > ahora` (EA-02 al consultar) | T:cu08::test_solo_vigentes_al_consultar_mas_recientes_primero; T:e2e::test_feed_paginado_y_jobs | **OK** | Expiración lógica: nunca se persiste `status: EXPIRED`. |
| RF-PUB-10 | Ver mis publicaciones activas | E | cu06/*; publicaciones.js | T:cu06::test_lista_solo_propias_vigentes_mas_recientes_primero, test_orden_descendente | **OK** |  |
| RF-PUB-11 | No permitir extender ni reactivar | E | Sin rutas de extensión ni reactivación; cu07/handler.py | T:cu07::test_autor_cierra_y_no_puede_reactivar | **OK** |  |
| RF-PUB-12 | Mostrar contador de caracteres | D | app.js `contador`; crear_publicacion.html | T:webjs::test_contador_de_caracteres | **OK** |  |
| RF-PUB-13 | Informar publicaciones activas disponibles | D | cu05/handler.py `cupo`; publicaciones.js | T:cu05::test_cupo; T:e2e::test_flujo_completo | **OK** |  |
| RF-PUB-14 | No ofrecer selección de duración | E | crear_publicacion.html | T:web::test_crear_publicacion_sin_duracion_ni_tipo_preseleccionado | **OK** |  |
| RF-PUB-15 | Informar la duración de la publicación | D | crear_publicacion.html | T:web::test_paginas_privadas_extienden_base_y_cargan_su_js | **OK** |  |
| RF-PUB-16 | Ignorar la duración enviada en la solicitud | E | cu05/request.py (`extra="ignore"`) | T:cu05::test_ignora_duracion_enviada | **OK** |  |

### FED — Feed «Ahora» (18)

| RF | Nombre | Prio. | Implementación | Test que lo verifica | Estado | Observación |
|---|---|---|---|---|---|---|
| RF-FED-01 | Listar publicaciones activas | E | cu08/* | T:cu08::test_paginado_por_bloques_de_20 | **OK** |  |
| RF-FED-02 | Excluir publicaciones no activas | E | cu08/repository.py (filtro) | T:cu08::test_solo_vigentes_al_consultar_mas_recientes_primero | **OK** |  |
| RF-FED-03 | Ordenar por más reciente | E | cu08/repository.py (orden `createdAt`, `_id`) | T:cu08::test_mismo_instante_ordena_por_orden_de_registro; T:e2e::test_feed_paginado_y_jobs | **OK** |  |
| RF-FED-04 | Mostrar datos de cada publicación | E | cu08/request.py; feed.js | T:cu08::test_no_expone_correo_y_tiempo_restante | **OK** |  |
| RF-FED-05 | Ver detalle de una publicación | E | cu09/* | T:cu09::test_detalle_de_publicacion_ajena | **OK** |  |
| RF-FED-06 | Informar feed vacío | D | cu08/handler.py `MSG_VACIO` | T:cu08::test_filtro_por_tipo_y_mensajes_de_vacio | **OK** |  |
| RF-FED-07 | Identificar publicaciones propias | E | cu08/handler.py `es_propia`; feed.js; detalle_publicacion.html | T:cu08::test_solo_vigentes_al_consultar_mas_recientes_primero | **OK** |  |
| RF-FED-08 | Actualizar el feed | E | feed.js (`setInterval` de 60 s) | T:web::test_archivos_estaticos | **OK** |  |
| RF-FED-09 | Actualizar el tiempo restante | D | app.js `refrescarRestantes` + `sincronizar` | T:web::test_utilidades_js_con_node | **OK** |  |
| RF-FED-10 | Informar publicación no disponible | E | cu09/handler.py | T:cu09::test_no_disponible_si_vencio_o_no_existe | **OK** |  |
| RF-FED-11 | Actualizar el feed manualmente | D | feed.html `#actualizar`; feed.js | T:webjs::test_feed_actualizar_a_demanda | **OK** |  |
| RF-FED-12 | No ofrecer acciones sobre publicaciones propias | E | cu09/handler.py; feed.js (tarjetas sin acciones) | T:cu09::test_propia_sin_responder_ni_reportar | **OK** |  |
| RF-FED-13 | Filtrar el feed por tipo | E | cu08/repository.py (filtro `type`) | T:cu08::test_filtro_por_tipo_y_mensajes_de_vacio | **OK** |  |
| RF-FED-15 | Informar que no hay publicaciones del tipo seleccionado | D | cu08/handler.py `MSG_VACIO_TIPO` | T:cu08::test_filtro_por_tipo_y_mensajes_de_vacio | **OK** |  |
| RF-FED-16 | Quitar el filtro | D | feed.js `quitarFiltro` (botón «Ver todos») | T:webjs::test_feed_quitar_filtro | **OK** |  |
| RF-FED-17 | Aplicar el filtro en las actualizaciones del feed | E | feed.js `url()` conserva el filtro | T:webjs::test_feed_filtro_se_mantiene_en_actualizaciones | **OK** |  |
| RF-FED-18 | Ofrecer la selección del tipo | E | feed.html (`Todos` seleccionado) | T:web::test_feed_ofrece_todos_y_los_tres_tipos | **OK** |  |
| RF-FED-19 | Cargar el siguiente bloque del feed | E | cu08/repository.py (cursor); feed.js `IntersectionObserver` | T:cu08::test_paginado_por_bloques_de_20; T:e2e::test_feed_paginado_y_jobs | **OK** |  |

### CHT — Respuestas y chat (26)

| RF | Nombre | Prio. | Implementación | Test que lo verifica | Estado | Observación |
|---|---|---|---|---|---|---|
| RF-CHT-01 | Exigir primer mensaje al responder | E | reglas.py `validar_contenido_mensaje`; cu10/request.py | T:cu10::test_validacion_del_mensaje | **OK** |  |
| RF-CHT-02 | Crear chat 1 a 1 | E | cu10/handler.py, cu10/repository.py | T:cu10::test_crea_chat_y_primer_mensaje | **OK** |  |
| RF-CHT-03 | Iniciar el conteo de inactividad | E | cu10/handler.py | T:cu10::test_crea_chat_y_primer_mensaje | **OK** |  |
| RF-CHT-04 | No permitir responder a la propia publicación | E | cu10/handler.py | T:cu10::test_no_responder_propia_ni_no_activa; T:e2e::test_flujo_completo | **OK** |  |
| RF-CHT-05 | Limitar a un chat activo por usuario y publicación | E | cu10/handler.py; índice `uq_chats_pub_responder` | T:cu10::test_un_chat_activo_por_usuario_y_publicacion | **OK** |  |
| RF-CHT-06 | Rechazar respuestas a publicaciones no activas | E | cu10/handler.py | T:cu10::test_no_responder_propia_ni_no_activa | **OK** |  |
| RF-CHT-07 | Permitir múltiples respuestas | E | cu10/handler.py | T:cu10::test_un_chat_activo_por_usuario_y_publicacion | **OK** |  |
| RF-CHT-08 | Enviar mensajes de texto | E | reglas.py `validar_contenido_mensaje` | T:cu10::test_validacion_del_mensaje; T:cu11::test_mensaje_reinicia_expiracion | **OK** |  |
| RF-CHT-09 | Enviar imágenes | E | reglas.py `validar_imagen`; storage/image_storage.py (guarda `storageBucket`) | T:cu11::test_imagen_con_url_protegida; T:shared::test_rechaza_formato_y_tamano, test_mensaje_guarda_storage_bucket | **OK** | El navegador recomprime las imágenes de más de 4 MB antes de subirlas (límite de Vercel). |
| RF-CHT-10 | No permitir otros medios | E | reglas.py `validar_imagen` | T:shared::test_rechaza_formato_y_tamano | **OK** |  |
| RF-CHT-11 | Mostrar los mensajes del chat | E | cu12/repository.py (orden); clock.py `hora_hhmm` (America/Lima); campo `hora` | T:cu12::test_abrir_no_reinicia_expiracion_y_marca_propios; T:cu11::test_mensaje_reinicia_expiracion; T:shared::test_hora_hhmm_en_america_lima | **OK** | Corregido: HH:MM calculada en el servidor en America/Lima (commit `f6a3b3f`). |
| RF-CHT-12 | Reiniciar el conteo de inactividad | E | cu11/repository.py | T:cu11::test_mensaje_reinicia_expiracion; T:cu12::test_abrir_no_reinicia_expiracion_y_marca_propios | **OK** |  |
| RF-CHT-13 | Expirar chat por inactividad | E | entities.py `Chat.activo`; ea03/* | T:cu11::test_chat_expirado_no_admite_mensajes; T:ea03::test_elimina_solo_chats_expirados_con_mensajes_e_imagenes | **OK** |  |
| RF-CHT-14 | Avisar la expiración próxima | E | cu12/handler.py `_calcular_aviso`; chat.js | T:cu12::test_aviso_ea04_con_anticipacion_configurable | **OK** |  |
| RF-CHT-15 | Cerrar el acceso a un chat expirado | E | cu11/handler.py; cu12/handler.py `_chat_vigente` | T:cu12::test_chat_expirado_o_ajeno; T:cu11::test_chat_expirado_no_admite_mensajes | **OK** |  |
| RF-CHT-16 | Eliminar el contenido de un chat expirado | E | ea03/* | T:ea03::test_elimina_solo_chats_expirados_con_mensajes_e_imagenes; T:e2e::test_feed_paginado_y_jobs | **OK** |  |
| RF-CHT-17 | Mantener chats abiertos al expirar la publicación | E | cu07/handler.py (no toca los chats) | T:e2e::test_flujo_completo («el chat sigue tras cerrar la publicación») | **OK** | Solo lo verifica la prueba e2e (ejecutada en esta auditoría). |
| RF-CHT-18 | Ver mis chats activos | E | cu12/handler.py `handle` (`hora_ultimo_mensaje`); chat.js | T:cu12::test_lista_por_ultimo_mensaje_con_no_leidos | **OK** | Corregido junto con RF-CHT-11. |
| RF-CHT-19 | Abrir un chat desde la lista | E | cu12/handler.py `abrir` | T:cu12::test_abrir_no_reinicia_expiracion_y_marca_propios | **OK** |  |
| RF-CHT-20 | Recibir mensajes sin recargar | E | chat.js (sondeo cada 1 s) | T:web::test_archivos_estaticos; T:cu12::test_sondeo_incremental | **OK** |  |
| RF-CHT-21 | Indicar mensajes no leídos | D | cu12/* `lastReadAt` | T:cu12::test_lista_por_ultimo_mensaje_con_no_leidos | **OK** |  |
| RF-CHT-22 | Mostrar el contexto del chat | D | mapeo.py (contexto desnormalizado en chats); chat.html | T:cu12::test_abrir_no_reinicia_expiracion_y_marca_propios; T:cu10::test_crea_chat_y_primer_mensaje | **OK** |  |
| RF-CHT-23 | Ofrecer abrir el chat existente | D | cu09/handler.py `chat_existente_id`; cu10/handler.py | T:cu09::test_ofrece_chat_existente; T:cu10::test_un_chat_activo_por_usuario_y_publicacion | **OK** |  |
| RF-CHT-24 | Permitir responder de nuevo tras la expiración | E | cu10/handler.py, cu10/repository.py `eliminar_chat` | T:cu10::test_responder_de_nuevo_tras_expirar_crea_chat_nuevo | **OK** |  |
| RF-CHT-25 | Informar la expiración con el chat abierto | D | cu11/cu12 `MSG_EXPIRADO`; chat.js `marcarExpirado` | T:cu11::test_chat_expirado_no_admite_mensajes | **OK** | La desactivación del formulario solo está en el JS y no tiene test. |
| RF-CHT-26 | Validar la imagen por su contenido | E | reglas.py `detectar_formato_imagen`; image_storage.py `recodificar_sin_metadatos` | T:shared::test_detecta_formato_por_contenido, test_imagen_corrupta_con_firma_valida_se_rechaza | **OK** |  |

### REP — Reportes (17)

| RF | Nombre | Prio. | Implementación | Test que lo verifica | Estado | Observación |
|---|---|---|---|---|---|---|
| RF-REP-01 | Reportar una publicación | E | cu13/* | T:cu13::test_registra_reporte_con_copia_y_plazo | **OK** |  |
| RF-REP-02 | Reportar un chat | E | cu14/* | T:cu14::test_snapshot_de_textos_e_imagenes_retenidas, test_solo_participantes_de_chat_activo | **OK** |  |
| RF-REP-03 | Exigir motivo del reporte | E | cu13/request.py, cu14/request.py; entities.py `MOTIVOS_REPORTE` | T:cu13::test_validaciones; T:web::test_reportar_ofrece_los_cinco_motivos | **OK** |  |
| RF-REP-04 | Permitir observación opcional | E | cu13/request.py, cu14/request.py | T:cu13::test_validaciones | **OK** |  |
| RF-REP-05 | Conservar el reporte | E | cu13/handler.py, cu14/handler.py; mapeo.py | T:cu13::test_registra_reporte_con_copia_y_plazo | **OK** |  |
| RF-REP-06 | Conservar el contenido de una publicación reportada | E | cu13/handler.py (`publicationData`) | T:cu13::test_registra_reporte_con_copia_y_plazo; T:shared::test_snapshot_de_reporte_con_captured_at_y_publication_data | **OK** |  |
| RF-REP-07 | Conservar los identificadores | E | cu13/handler.py, cu14/handler.py | T:cu13::test_registra_reporte_con_copia_y_plazo; T:cu14::test_snapshot_de_textos_e_imagenes_retenidas | **OK** |  |
| RF-REP-08 | Conservar durante el plazo | E | `retentionEndsAt`; ea05/* | T:cu13::test_plazo_configurable; T:ea05::test_purga_al_vencer_el_plazo_de_cada_reporte | **OK** |  |
| RF-REP-09 | Eliminar al vencer el plazo | E | ea05/* | T:ea05::test_purga_al_vencer_el_plazo_de_cada_reporte; T:e2e::test_feed_paginado_y_jobs | **OK** |  |
| RF-REP-10 | No interrumpir el elemento reportado | E | cu13/cu14 (no modifican el objeto reportado) | T:cu13::test_registra_reporte_con_copia_y_plazo | **OK** |  |
| RF-REP-11 | No ofrecer gestión de reportes en la aplicación | E | No existe ninguna ruta para consultar ni gestionar reportes | T:conf::test_sin_funciones_de_gestion_de_reportes | **OK** |  |
| RF-REP-12 | Impedir reporte duplicado de una publicación | E | cu13/handler.py | T:cu13::test_duplicado_y_propia | **OK** |  |
| RF-REP-13 | Impedir reportar la propia publicación | E | cu13/handler.py | T:cu13::test_duplicado_y_propia; T:e2e::test_flujo_completo | **OK** |  |
| RF-REP-14 | Confirmar el reporte al reportante | D | cu13/handler.py, cu14/handler.py | T:cu13::test_registra_reporte_con_copia_y_plazo | **OK** |  |
| RF-REP-15 | Mantener la confidencialidad del reporte | E | Ninguna respuesta expone reportes | T:conf::test_reporte_de_publicacion_invisible_para_el_reportado_y_terceros, test_reporte_de_chat_invisible_para_el_otro_participante | **OK** |  |
| RF-REP-16 | Permitir reportes sucesivos de un chat | E | cu14/handler.py | T:cu14::test_reportes_sucesivos_permitidos | **OK** |  |
| RF-REP-17 | Conservar el contenido de un chat reportado | E | cu14/handler.py (`messagesSnapshot` con las claves del Entregable 2); image_storage.py `copiar_a_retencion` | T:cu14::test_snapshot_de_textos_e_imagenes_retenidas | **OK** |  |

### CFG — Configuración (10)

| RF | Nombre | Prio. | Implementación | Test que lo verifica | Estado | Observación |
|---|---|---|---|---|---|---|
| RF-CFG-01 | Configurar el dominio institucional | E | config/provider.py; reglas.py `validar_parametro` | T:cu15::test_acepta_valores_en_rango; T:shared::test_config_valores_iniciales_del_srs | **OK** |  |
| RF-CFG-03 | Configurar el máximo de publicaciones activas | E | config/provider.py; cu05/handler.py | T:cu05::test_limite_de_activas_configurable; T:cu15::test_acepta_valores_en_rango | **OK** |  |
| RF-CFG-05 | Configurar la anticipación del aviso | E | cu12/handler.py `_calcular_aviso`; reglas.py | T:cu12::test_aviso_ea04_con_anticipacion_configurable; T:cu15::test_rechaza_fuera_de_rango_o_formato | **OK** |  |
| RF-CFG-06 | Configurar el plazo de conservación | E | cu13/handler.py, cu14/handler.py | T:cu13::test_plazo_configurable | **OK** |  |
| RF-CFG-07 | Configurar la inactividad de la sesión | E | security/session.py `vencimiento_sesion`; cu02/handler.py | T:cu02::test_inicio_exitoso_crea_sesion_de_12_horas; T:cu15::test_acepta_valores_en_rango | **OK** |  |
| RF-CFG-08 | No ofrecer pantalla de administración | E | cu15/endpoint.py (router vacío; solo CLI) | T:cu15::test_sin_endpoint_publico | **OK** |  |
| RF-CFG-09 | Validar los valores de los parámetros | E | config/provider.py (conserva el último valor válido y lo registra) | T:shared::test_config_fuera_de_rango_conserva_ultimo_valido; T:cu15::test_rechaza_fuera_de_rango_o_formato | **OK** |  |
| RF-CFG-10 | Aplicar los cambios de plazo solo a operaciones nuevas | E | Plazos guardados en cada documento (`retentionEndsAt`, `expiresAt`) | T:ea05::test_purga_al_vencer_el_plazo_de_cada_reporte | **OK** |  |
| RF-CFG-11 | Conservar el vencimiento de las sesiones existentes | E | security/session.py (recalcula en la siguiente interacción) | T:shared::test_cambio_de_inactividad_aplica_desde_la_siguiente_interaccion | **OK** |  |
| RF-CFG-12 | Conservar el acceso de las cuentas existentes | E | cu02/handler.py (no valida el dominio al iniciar sesión); `validationLevel: moderate` | T:cu02::test_cuenta_existente_conserva_acceso_al_cambiar_el_dominio, test_validador_de_accounts_moderado_para_cuentas_de_un_dominio_anterior | **OK** |  |

## 3. Reglas de negocio (RN-01 a RN-50)

| RN | Implementación | Test que la verifica | Estado | Observación |
|---|---|---|---|---|
| RN-01 | cu01/handler.py; reglas.py `correo_del_dominio` | T:cu01::test_rechaza_otro_dominio_y_subdominio | **OK** |  |
| RN-02 | cu17/* | T:cu17::test_activa_con_enlace_vigente_una_sola_vez | **OK** |  |
| RN-03 | cu01/handler.py; `uq_accounts_email` | T:cu01::test_rechaza_correo_activo_o_pendiente | **OK** |  |
| RN-04 | DTO de respuesta sin correo | T:cu08::test_no_expone_correo_y_tiempo_restante; T:cu12::test_abrir_no_reinicia_expiracion_y_marca_propios | **OK** |  |
| RN-05 | reglas.py `validar_nickname`; cu04/*; colación | T:shared::test_nickname_*; T:cu04::* | **OK** |  |
| RN-06 | security/session.py | T:shared::test_sesion_* | **OK** |  |
| RN-07 | entities.py `TipoPublicacion`; cu05/request.py | T:cu05::test_validaciones | **OK** |  |
| RN-08 | cu05/request.py | T:cu05::test_validaciones, test_limites_exactos_aceptados | **OK** |  |
| RN-09 | entities.py `DURACION_PUBLICACION`; cu05 | T:cu05::test_crea_con_duracion_fija_de_24_horas, test_ignora_duracion_enviada | **OK** |  |
| RN-10 | cu05/repository.py (transacción) | T:cu05::test_limite_de_activas_configurable; T:e2e-cupo | **OK** |  |
| RN-11 | cu07/*; `Publicacion.activa` | T:cu07::test_autor_cierra_y_no_puede_reactivar | **OK** |  |
| RN-12 | cu08, cu09, cu10 | T:cu08::test_solo_vigentes_*; T:cu10::test_no_responder_propia_ni_no_activa | **OK** |  |
| RN-13 | cu07 no toca chats; contexto desnormalizado | T:e2e::test_flujo_completo | **OK** | Solo e2e (ejecutada). |
| RN-14 | cu10 (sin límite) | T:cu10::test_un_chat_activo_por_usuario_y_publicacion | **OK** |  |
| RN-15 | cu10/handler.py; cu09 | T:cu10::test_no_responder_propia_ni_no_activa | **OK** |  |
| RN-16 | cu10; `uq_chats_pub_responder` | T:cu10::test_un_chat_activo_*, test_responder_de_nuevo_tras_expirar_crea_chat_nuevo | **OK** |  |
| RN-17 | cu11/cu12 (participantes); ruta protegida de imágenes | T:cu12::test_imagen_solo_para_participantes; T:cu11::test_tercero_no_puede_enviar | **OK** |  |
| RN-18 | cu10 (chat + primer mensaje en transacción) | T:cu10::test_crea_chat_y_primer_mensaje | **OK** |  |
| RN-19 | reglas.py `validar_contenido_mensaje`, `validar_imagen` | T:cu10::test_validacion_del_mensaje; T:shared::test_rechaza_formato_y_tamano | **OK** |  |
| RN-20 | cu11/repository.py; `Chat.activo` | T:cu11::test_mensaje_reinicia_expiracion; T:cu12::test_abrir_no_reinicia_* | **OK** |  |
| RN-21 | cu12 `_calcular_aviso` | T:cu12::test_aviso_ea04_con_anticipacion_configurable | **OK** |  |
| RN-22 | ea03/*; `_chat_vigente` | T:ea03::test_elimina_solo_chats_expirados_* | **OK** |  |
| RN-23 | cu13/cu14 | T:cu13::test_validaciones; T:cu14::* | **OK** |  |
| RN-24 | cu13/cu14 (instantánea en el momento); ea05 | T:cu13::test_registra_reporte_con_copia_y_plazo; T:cu14::test_snapshot_* | **OK** |  |
| RN-25 | cu13/cu14 | T:cu13::test_registra_reporte_con_copia_y_plazo | **OK** |  |
| RN-26 | ea05/* | T:ea05::test_purga_al_vencer_el_plazo_de_cada_reporte | **OK** |  |
| RN-27 | config/provider.py; cu15 | T:cu15::*; T:shared::test_config_* | **OK** |  |
| RN-28 | cu06, cu12 | T:cu06::*; T:cu12::test_lista_* | **OK** |  |
| RN-29 | cu08, cu09; feed.js | T:cu08::*; T:cu09::test_propia_sin_responder_ni_reportar | **OK** |  |
| RN-30 | reglas.py `validar_contrasena`, `validar_confirmacion` | T:shared::test_politica_contrasena, test_confirmacion | **OK** |  |
| RN-31 | registro.html; cu16 (canal ARCO desde `CANAL_ARCO`); web/terminos/terminos.txt; provider.py `verificar_entorno` | T:web::test_registro_casilla_desmarcada; T:cu16::test_politica_completa_rn31_con_canal_arco_configurado; T:shared::test_produccion_exige_version_fecha_y_canal_arco_de_la_politica | **OK** | El valor real de `CANAL_ARCO` y la versión y fecha del texto aprobado debe aportarlos la institución; en producción la app no arranca sin ellos. |
| RN-32 | reglas.py `normalizar_texto` | T:cu05::test_crea_con_duracion_fija_de_24_horas; T:cu13::test_validaciones | **OK** |  |
| RN-33 | reglas.py; colación del nickname | T:cu01::test_rechaza_otro_dominio_y_subdominio, test_nickname_ocupado_* | **OK** |  |
| RN-34 | clock.py (UTC en el servidor) y `hora_hhmm` (America/Lima) | T:shared::test_relojes, test_hora_hhmm_en_america_lima | **OK** |  |
| RN-35 | cu13 (propia, duplicado); cu14 (sucesivos) | T:cu13::test_duplicado_y_propia; T:cu14::test_reportes_sucesivos_permitidos | **OK** |  |
| RN-36 | Sin exposición de reportes | T:conf::test_reporte_de_publicacion_invisible_para_el_reportado_y_terceros, test_reporte_de_chat_invisible_para_el_otro_participante | **OK** |  |
| RN-37 | Sin rutas de gestión de reportes; copias retenidas solo en `reports/` | T:conf::test_sin_funciones_de_gestion_de_reportes, test_contenido_conservado_inaccesible_desde_la_aplicacion | **OK** |  |
| RN-38 | cu02, cu03 | T:cu02::test_sesiones_simultaneas; T:cu03::test_cierra_solo_la_sesion_actual | **OK** |  |
| RN-39 | cu02/handler.py; `IntentoAcceso.registrar_fallo` | T:cu02::test_ventana_movil_de_15_minutos, test_bloqueo_* | **OK** |  |
| RN-40 | cu01, cu02, security/session.py | T:cu02::test_cuenta_pendiente_no_obtiene_sesion | **OK** |  |
| RN-41 | cu17; SecureTokenService | T:cu17::*; T:shared::test_tokens_de_128_bits_o_mas_y_unicos | **OK** |  |
| RN-42 | cu17 `reenviar` | T:cu17::test_reenvio_limite_5_en_24h_con_mismo_mensaje | **OK** |  |
| RN-43 | ea07 (`ix_accounts_activation_exp`); `pendiente_vencida` | T:ea07::*; T:cu01::test_pendiente_vencida_libera_correo_y_nickname | **OK** |  |
| RN-44 | cu08 (filtro); feed.html | T:cu08::test_filtro_por_tipo_y_mensajes_de_vacio; T:web::test_feed_ofrece_todos_y_los_tres_tipos | **OK** |  |
| RN-45 | feed.js conserva el filtro; el filtro no modifica datos | T:webjs::test_feed_filtro_se_mantiene_en_actualizaciones; T:cu08::test_filtro_no_altera_las_publicaciones_ni_su_vencimiento | **OK** |  |
| RN-46 | cu18 | T:cu18::test_enlace_vence_a_los_30_minutos, test_flujo_completo_* | **OK** |  |
| RN-47 | cu18 `handle` | T:cu18::test_respuesta_uniforme_sin_cuenta_o_cuenta_pendiente | **OK** |  |
| RN-48 | cu18/repository.py `cerrar_sesiones_de` | T:cu18::test_flujo_completo_cierra_todas_las_sesiones | **OK** |  |
| RN-49 | cu17 `reenviar` | T:cu17::test_reenvio_misma_respuesta_si_no_hay_cuenta_pendiente | **OK** |  |
| RN-50 | cu18 `handle` | T:cu18::test_nuevo_enlace_invalida_el_anterior_y_limite_5 | **OK** |  |

## 4. Requisitos no funcionales (38)

| RNF | Exigencia (resumen) | Implementación | Test / evidencia | Estado | Observación |
|---|---|---|---|---|---|
| RNF-REN-01 | 100 usuarios simultáneos, < 1 % de errores | Índices, sondeo incremental | Locust 15 min, perfil del criterio: tests/carga/ejecutar_carga.py (resultados/resumen.json) | **OK** | 0 errores en 29 135 solicitudes (local). **Despliegue:** repetir contra Vercel + Atlas. |
| RNF-REN-02 | Primer bloque del feed ≤ 3 s (p95) con 3 000 activas | `ix_publications_feed`, bloques de 20 con cursor | Locust: tests/carga/ejecutar_carga.py (resultados/resumen.json) | **OK** | p95 0,68 s sin filtro y 0,31 s con filtro (local). **Despliegue:** repetir en producción. |
| RNF-REN-03 | Texto visible ≤ 2 s (p95) | Sondeo cada 1 s (chat.js) | Locust (entrega medida en el otro participante): tests/carga/ejecutar_carga.py (resultados/resumen.json) | **OK** | p95 0,39 s (local). **Despliegue:** repetir en producción. |
| RNF-REN-04 | Imagen de 5 MB visible ≤ 10 s (p95) | Compresión en el cliente > 4 MB; image_storage.py | 20 envíos de ~5 MB: tests/carga/ejecutar_carga.py (resultados/resumen.json) | **OK** | p95 7,63 s = tiempo local + transferencia calculada a 10 Mbps (la red no se emula). **Despliegue:** repetir con red real y Object Storage. |
| RNF-REN-05 | Correo en cola ≤ 30 s (p95) | email/sender.py (envío dentro de la solicitud) | 100 registros: tests/carga/ejecutar_carga.py (resultados/resumen.json) | **OK** | p95 0,34 s con el emisor de desarrollo. **Despliegue:** repetir con el SMTP real. |
| RNF-REN-06 | REN-02/03 con 10 000 cuentas | Índices | Locust con 10 000 cuentas y 3 000 publicaciones activas: tests/carga/ejecutar_carga.py (resultados/resumen.json) | **OK** | **Despliegue:** repetir en producción. |
| RNF-DIS-01 | Disponibilidad ≥ 99 % / 30 días | — | — | **FALTA** | **Despliegue:** requiere un monitor externo que consulte la página de inicio cada minuto (p. ej. UptimeRobot o Better Stack); no es código de la app. |
| RNF-FIA-01 | Plazos con desviación ≤ 1 min | Evaluación al consultar (DD-03), FakeClock | T:cu02::test_bloqueo_*; T:cu12::test_aviso_*; T:shared::test_sesion_* | **OK** |  |
| RNF-FIA-02 | Tras una caída, aplicar plazos vencidos en ≤ 1 min | app/jobs/arranque.py (EA-03/05/07 al arrancar); EA-07 sin hint si falta el índice | T:e2e-rob::test_fia_02_plazos_vencidos_durante_la_caida_se_aplican_al_arrancar; T:rob::test_el_arranque_programa_los_plazos_vencidos | **OK** |  |
| RNF-FIA-03 | Operaciones atómicas | mongo.py `en_transaccion`; cu05, cu10, cu11 | T:tx::*; T:cu10::test_imagen_corrupta_no_deja_chat, test_fallo_al_crear_borra_la_imagen; T:cu14::test_fallo_al_registrar_no_deja_copias | **OK** |  |
| RNF-SEG-01 | Sesión obligatoria salvo funciones exceptuadas | `get_sesion_actual` / `get_sesion_opcional` | T:web::test_paginas_privadas_sin_sesion_redirigen; T:e2e::test_flujo_completo | **OK** |  |
| RNF-SEG-02 | bcrypt con costo ≥ 10 | hashing.py (costo 12 + prehash SHA-256) | T:shared::test_bcrypt_con_sal_y_contrasena_larga, test_costo_por_defecto_es_12 | **OK** |  |
| RNF-SEG-03 | HTTPS con TLS ≥ 1.2 | app/shared/web/https.py: HTTP → HTTPS (308) y HSTS con ENTORNO=produccion | T:rob::test_http_se_redirige_a_https_en_produccion, test_proxy_que_termina_tls_x_forwarded_proto | **PARCIAL** | La redirección y HSTS están probadas. **Despliegue:** la versión de TLS (rechazar 1.0/1.1) la negocia Vercel y solo se verifica contra el dominio publicado. |
| RNF-SEG-04 | Chat e imágenes solo para participantes | cu11/cu12 `_chat_vigente`; ruta de imagen con sesión | T:cu12::test_imagen_solo_para_participantes; T:e2e::test_flujo_completo | **OK** |  |
| RNF-SEG-05 | Texto literal, sin HTML | Autoescape de Jinja2; `textContent` en JS | T:web::test_nickname_se_escapa, test_archivos_estaticos | **OK** |  |
| RNF-SEG-06 | Identificador ≥ 128 bits; HttpOnly, Secure, SameSite=Lax | hashing.py (256 bits); session.py | T:cu02::test_endpoint_escribe_cookie_segura; T:shared::test_tokens_* | **OK** |  |
| RNF-SEG-07 | Sesión invalidada no reutilizable | session.py; cu03 | T:shared::test_sesion_expirada_queda_invalidada; T:cu03::* | **OK** |  |
| RNF-PRI-01 | Correo no visible para otros | DTO sin correo | T:cu08::test_no_expone_correo_*; T:e2e::test_flujo_completo | **OK** |  |
| RNF-PRI-02 | Contenido reportado eliminado ≤ 24 h; respaldos ≤ 7 días | ea05 (cron horario y al arrancar); scripts/respaldo_mongodb.py; .github/workflows/backup.yml (artifact cifrado, 7 días) | T:ea05::*; T:scripts::test_rota_respaldos_de_mas_de_7_dias; T:wf::* | **PARCIAL** | **Grupo:** el respaldo diario se activa al crear los secrets `MONGO_URI` y `BACKUP_PASSPHRASE`. **Despliegue:** si se usan snapshots de Atlas, su retención (≤ 7 días) se configura en Atlas. |
| RNF-PRI-03 | Chat expirado eliminado ≤ 24 h | ea03 (cron horario y al arrancar) | T:ea03::*; T:ea07::test_workflow_* | **OK** |  |
| RNF-PRI-04 | Imágenes sin EXIF | image_storage.py `recodificar_sin_metadatos` | T:shared::test_imagen_se_recodifica_sin_exif; T:cu10::test_primer_mensaje_con_imagen_sin_exif | **OK** |  |
| RNF-PRI-05 | Logs sin texto ni imágenes de chats | Ningún `log.*` incluye contenido de mensajes | T:rob::test_registros_tecnicos_sin_texto_ni_imagenes_de_chats | **OK** |  |
| RNF-LEG-01 | Consentimiento expreso y registrado | registro.html; cu01 `termsAcceptance` | T:web::test_registro_casilla_desmarcada; T:cu01::test_registro_* | **OK** | **Grupo:** `TERMINOS_VERSION` y `TERMINOS_FECHA` del texto aprobado (obligatorias en producción). |
| RNF-LEG-02 | Política: datos, finalidad, plazos, quién accede | web/terminos/terminos.txt (incluye respaldos, PA-37) | T:cu16::test_politica_completa_rn31_con_canal_arco_configurado | **OK** | **Grupo:** aprobación del texto legal. |
| RNF-LEG-03 | Canal ARCO en la política | terminos.txt + variable `CANAL_ARCO` (obligatoria en producción) | T:cu16::test_politica_completa_rn31_con_canal_arco_configurado; T:shared::test_produccion_exige_version_fecha_y_canal_arco_de_la_politica | **OK** | **Grupo:** el canal concreto lo define la institución. |
| RNF-USA-01 | Formato «X h Y min» / «X h» / «Y min» / «menos de 1 min» | app.js `restante` | T:web::test_utilidades_js_con_node | **OK** |  |
| RNF-USA-02 | Uso en PC y móvil desde 360 px | Bootstrap 5, viewport | T:nav-a11y::test_360_px_sin_desplazamiento_horizontal (17 pantallas, 3 motores) | **OK** |  |
| RNF-USA-03 | Mensaje junto al campo afectado | app.js `mostrarErrores` (aria-describedby, aria-invalid, foco); `campo` en errores de dominio | T:nav-form::* | **OK** |  |
| RNF-USA-04 | Contraste ≥ 4,5:1 | app.css (botones outline oscurecidos) | T:nav-a11y::test_axe_sin_violaciones_serias_de_contraste_ni_etiquetas (axe-core, 360 y 1366 px) | **OK** |  |
| RNF-USA-05 | Interfaz y mensajes en español | validacion.py (errores de Pydantic); main.py (404/405 en HTML o JSON) | T:webval::*; T:webhttp::* | **OK** |  |
| RNF-USA-06 | Conservar datos tras un error, excepto contraseñas | app.js `vaciarContrasenas`; acceso.js | T:nav-form::test_registro_error_de_dominio_junto_al_correo_y_vacia_contrasenas, test_login_fallido_vacia_la_contrasena_y_conserva_el_correo | **OK** |  |
| RNF-USA-07 | Etiqueta visible en todo campo | Plantillas (sin visually-hidden) | T:web::test_campos_con_etiqueta_visible; T:nav-form::test_filtro_del_feed_tiene_etiqueta_visible; axe-core | **OK** |  |
| RNF-USA-08 | Todo usable con teclado (PC) | Controles nativos; el chat devuelve el foco al campo tras enviar | T:nav-a11y::test_flujo_principal_solo_con_teclado (Chromium y Firefox) | **OK** | En WebKit se omite: como en Safari por defecto, Tab no recorre enlaces, y Safari en PC no está entre los navegadores de RNF-COM-01. |
| RNF-COM-01 | Chrome, Firefox, Edge (PC); Chrome Android; Safari iOS | APIs estándar | T:nav-compat::test_flujos_principales (Chromium, Firefox y WebKit; Pixel 7 e iPhone 14 emulados) | **PARCIAL** | Los flujos pasan en los tres motores y en móviles emulados. **Grupo:** el criterio pide las dos últimas versiones estables de cada navegador y Chrome en Android y Safari en iOS reales; la emulación no lo sustituye. |
| RNF-MAN-01 | Parámetros sin recompilar | config/provider.py (variables de entorno) | T:shared::test_config_*; T:cu15::* | **OK** |  |
| RNF-MAN-02 | Reloj de pruebas controlable | clock.py `RelojDePruebas` + /pruebas/reloj con ENTORNO=pruebas | T:e2e-rob::test_man_02_adelantar_24_y_72_horas; T:rob::test_reloj_de_pruebas_* | **OK** | Un solo worker en el entorno de pruebas (el desfase vive en memoria). |
| RNF-SEG-08 | Tokens de enlaces ≥ 128 bits | hashing.py (256 bits, `secrets`) | T:shared::test_tokens_de_128_bits_o_mas_y_unicos | **OK** |  |
| RNF-SEG-09 | Tokens de un solo uso | cu17/cu18 `find_one_and_update` atómico | T:cu17::test_activa_con_enlace_vigente_una_sola_vez; T:cu18::test_flujo_completo_* | **OK** |  |

## 5. Comparación con el Entregable 2 (modelo físico MongoDB)

Fuente en el código: `app/shared/db/mongo.py` (`crear_indices`, validadores), `app/shared/db/mapeo.py` (nombres de campo) y los repositorios de los jobs. Fuente en el Entregable 2: §5.3 (documentos BSON), §5.4 (catálogo de índices), §6 (diccionario, Tablas 6.1–6.8), §7.3 (crecimiento) y Anexo B (`db_init_la_banca.js`).

### 5.1 Colecciones

Las 8 coinciden: `accounts`, `login_attempts`, `sessions`, `publications`, `chats`, `messages`, `reports` y `system_parameters`, en la base `la_banca_db`. El código las crea todas al arrancar; el Anexo B solo crea explícitamente `accounts` y `login_attempts`.

### 5.2 Índices

| Colección | Índice | Entregable 2 | Código | Diferencia |
|---|---|---|---|---|
| accounts | `uq_accounts_email` `{email:1}` único | §5.4 y Anexo B | Sí | — |
| accounts | `uq_accounts_nickname` `{nickname:1}` único | §5.4 y Anexo B (sin colación) | Sí, con **colación `en`, strength 2** | El código hace la unicidad sin distinguir mayúsculas (RN-05/RN-33). El índice del Entregable 2 admitiría «Ana_07» y «ana_07». |
| accounts | `ix_accounts_activation_exp` | §5.4 y Anexo B (para EA-07) | Sí, **usado por EA-07** (con `hint`) | Resuelto (`a8fea89`): la consulta acota `activation.expiresAt ≤ corte + 96 h` y mantiene la condición exacta `createdAt ≤ ahora − 72 h`. |
| accounts | `ix_accounts_activation_token`, `ix_accounts_reset_token` (sparse) | — | **Extra** | Búsqueda de los tokens de activación y de recuperación. |
| accounts | `ix_accounts_pending` `{status, createdAt}` | — | **Extra** | Lo usan las purgas al consultar de CU-01 y CU-17. |
| login_attempts | `uq_login_attempts_email`, `ttl_login_attempts_locked` | §5.4 y Anexo B | Sí | — |
| login_attempts | `ttl_login_attempts_cleanup` (TTL 900 s) | Solo Anexo B | Sí | Incoherencia interna del Entregable 2 (§5.4 no lo lista). |
| sessions | `uq_sessions_token` `{tokenHash:1}` único | Tabla 6.3 dice UNIQUE, pero no está en §5.4 ni en el Anexo B | **Extra** | El código cubre lo que exige el diccionario. |
| sessions | `ix_sessions_user_status` | §5.4 y Anexo B | Sí | — |
| sessions | `ix_sessions_exp` | Solo Anexo B | Sí, **usado por la purga de EA-07** | — |
| publications | `ix_publications_feed`, `ix_publications_author_act` | §5.4 y Anexo B | Sí | El feed sin filtro (`Todos`) no fija `type`, así que no aprovecha el prefijo `status, type`, y el `_id` de desempate no está en el índice. |
| chats | `uq_chats_pub_responder` único | §5.4 y Anexo B | Sí | El Entregable 2 lo justifica con RN-15; corresponde a RN-16. Para RF-CHT-24 el código borra el chat expirado antes de crear el nuevo. |
| chats | `ix_chats_participants_exp` | §5.4 y Anexo B | Sí | — |
| messages | `ix_messages_chat_sent` | §5.4 y Anexo B | Sí | — |
| reports | `ix_reports_retention_end` | §5.4 y Anexo B | Sí | — |
| reports | `ix_reports_target` `{targetType, targetId}` | Solo Anexo B | Sí | No incluye `reporterId`, que la consulta de duplicados (RF-REP-12) también filtra. |

**Resumen:** están los 15 índices del Anexo B y el código añade 4. La única diferencia de definición es la colación de `uq_accounts_nickname`.

### 5.3 Validadores `$jsonSchema`

| Colección | Entregable 2 (Anexo B) | Código | Diferencia |
|---|---|---|---|
| accounts | `email` con `@unas\.edu\.pe$` fijo | Patrón con el **dominio configurado** y `validationLevel: "moderate"` | Dominio parametrizado (RF-CFG-01); las cuentas de un dominio anterior siguen editables (RF-CFG-12). |
| login_attempts | `failedCount` 1–5, fechas | Igual, más **`failedAt`** (arreglo de hasta 5 fechas) | Campo añadido para la ventana móvil de RN-39 (`0147a2a`). |
| sessions, publications, chats, messages, reports, system_parameters | Sin validador en el Anexo B (aunque §9.1 habla de «validación `$jsonSchema`» y las Tablas 6.3–6.8 definen CHECK) | Sin validador | Las restricciones del diccionario (estados, longitudes, `participants` de 2, `mimeType`, `sizeBytes ≤ 5 MB`, `observation ≤ 300`, `targetType`) solo las aplica la capa de aplicación. |

### 5.4 Campos de los documentos

| Colección | Estado respecto del Entregable 2 |
|---|---|
| accounts | **Campos extra:** `termsAcceptance {version, acceptedAt}` (RF-AUT-17; el diccionario no lo contempla), `activation.sentAt[]` y `passwordReset.sentAt[]` (ventana móvil de RN-42/RN-50) y `publicationsVersion` (serializa las creaciones de publicaciones, RF-PUB-06). `sentCount` es la cantidad de envíos en las últimas 24 h, no un acumulado. |
| login_attempts | Coincide, más `failedAt`. |
| sessions | Coincide. |
| publications | Coincide en campos; `status` nunca toma `EXPIRED` (expiración lógica). |
| chats | **Campos extra:** `publicationType`, `publicationTitle`, `authorNickname`, `responderNickname` (RF-CHT-22) y `lastReadAt` (RF-CHT-21). `status` nunca toma `EXPIRED`: el chat vencido se borra (EA-03). |
| messages | **Coincide:** `imageAttachment` incluye ahora `storageBucket` (`a3bab5b`). |
| reports | **Coincide con §5.3** (`a3bab5b`): `reportedContentSnapshot` tiene `offenderUserId`, `capturedAt`, `publicationData`, `messagesSnapshot` (arreglo con `messageId`, `senderId`, `text`, `imageKey`, `sentAt`, más `senderNickname`) y `retainedImageKeys`. En un reporte de chat, `publicationData` lleva el contexto de la publicación de origen (`publicationId`, `type`, `title`), en lugar del `null` del ejemplo. Los reportes con el formato anterior se siguen leyendo. |
| system_parameters | Los `_id` son los nombres de las variables (`DOMINIO_INSTITUCIONAL`, `CFG_…`), no los del ejemplo; son 5 parámetros (SRS §3.2), no ~12. Solo se escribe con el CLI de CU-15; la app lee las variables de entorno. |

### 5.5 Ciclo de vida, respaldos y otras diferencias

- **Sesiones:** resuelto (`4840b69`). EA-07 elimina las sesiones cuyo vencimiento supera los 30 días (§7.3: «conservando solo los últimos 30 días»). Se ejecuta en cada corrida del job (cada hora), no una vez al mes; el efecto es la misma retención de 30 días.
- **Publicaciones históricas:** no se purgan (el Entregable 2 lo acepta como «depuración histórica posterior», sin job definido).
- **Respaldos (§8.1):** `scripts/respaldo_mongodb.py` (`fc66244`) hace `mongodump --gzip --archive`. `.github/workflows/backup.yml` (`3f99195`) lo ejecuta a diario y guarda el volcado cifrado como artifact con retención de 7 días; se activa al crear los secrets `MONGO_URI` y `BACKUP_PASSPHRASE`. La regla de ciclo de vida del bucket de imágenes y la retención de snapshots de Atlas siguen siendo configuración de infraestructura no versionada.
- **Frecuencia de los jobs:** GitHub Actions cada hora más crons diarios de Vercel como respaldo (el Entregable 2 habla de «cron diario»).
- **Contradicción del Entregable 2 con el SRS:** §1.1 presenta como parámetros configurables la duración de 24 h de las publicaciones y la inactividad de 24 h del chat, que en el SRS v1.9 son constantes (§3.3, PA-31). El código sigue al SRS.
- **Coincidencias relevantes:** bcrypt con costo 12, tokens guardados como SHA-256, `authorNickname`/`senderNickname` desnormalizados y propagados al cambiar el nickname, imágenes fuera de MongoDB (prefijos `chats/` y `reports/`) y snapshot embebido 1:1 en `reports`.

## 6. Prueba de carga (RNF-REN-01 a RNF-REN-06)

Ejecutada con `python tests/carga/ejecutar_carga.py` el 2026-11-10 (01:23–01:39 UTC):
- **Escala:** 100 usuarios durante 15m; app con uvicorn y 4 workers; MongoDB 7 replica set en Docker, todo en el mismo equipo.
- **Datos:** 10000 cuentas y 3000 publicaciones activas al inicio (3030 al final).
- **Perfil (el del criterio de RNF-REN-01):** 60 % consulta el feed cada 30 s (la mitad con filtro), 30 % intercambia un mensaje cada 20 s con sondeo de 1 s del otro participante, y 10 % crea o cierra una publicación cada 2 min.
- **Mediciones fuera de Locust:** RNF-REN-04 y RNF-REN-05 se midieron después, con 1 worker (20 imágenes y 100 registros).

| RNF | Métrica | Valor | Límite | Cumple |
|---|---|---|---|---|
| RNF-REN-01 | tasa de errores (0/29135) | 0,0 % | 1,0 % | sí |
| RNF-REN-02 | p95 primer bloque del feed (con y sin filtro) | 0,68 s | 3,0 s | sí |
| RNF-REN-03 | p95 entrega de un mensaje de texto | 0,39 s | 2,0 s | sí |
| RNF-REN-04 | p95 imagen de 5 MB visible (incluye red de 10 Mbps) | 7,629 s | 10,0 s | sí |
| RNF-REN-05 | p95 registro → correo entregado al emisor | 0,338 s | 30,0 s | sí |
| RNF-REN-06 | REN-02 y REN-03 con 10000 cuentas y 3000 activas | 10000,0 cuentas | 10000 cuentas | sí |

| Medición | Solicitudes | Fallos | p50 | p95 | Máx. |
|---|---|---|---|---|---|
| REN-02 feed: primer bloque | 899 | 0 | 0,07 s | 0,68 s | 3,54 s |
| REN-02 feed: primer bloque con filtro | 901 | 0 | 0,06 s | 0,31 s | 3,51 s |
| REN-03 entrega de texto al otro participante | 1350 | 0 | 0,07 s | 0,39 s | 7,00 s |
| cerrar publicación | 40 | 0 | 0,07 s | 0,14 s | 0,16 s |
| crear publicación | 70 | 0 | 0,10 s | 2,80 s | 3,95 s |
| enviar mensaje de texto | 1350 | 0 | 0,04 s | 0,24 s | 6,82 s |
| iniciar sesión | 130 | 0 | 1,90 s | 4,10 s | 4,20 s |
| responder publicación | 30 | 0 | 0,07 s | 3,50 s | 4,23 s |
| sondeo del chat abierto (1 s) | 24365 | 0 | 0,02 s | 0,10 s | 8,47 s |

**Validez:** son mediciones en local, sin latencia de red real. Para RNF-REN-04 se sumó la transferencia de subida y bajada calculada a 10 Mbps. Los resultados deben confirmarse en el despliegue (Vercel + Atlas).
