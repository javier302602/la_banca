"""Flujo de punta a punta contra MongoDB real: los 18 CU, EA-02 a EA-07 y CU-15.

Ejecutar con `pytest -m e2e` (requiere un replica set; ver tests/e2e/conftest.py).
Las dos pruebas comparten la base y se ejecutan en orden: la segunda usa el chat y los reportes de la primera.
"""
import asyncio
import io
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.shared.email.sender import get_email_sender
from app.shared.storage.image_storage import get_image_storage

cron = {"Authorization": "Bearer s3cr3t"}


def ok(condicion, mensaje):
    assert condicion, mensaje


def cliente():
    return TestClient(app, base_url="https://testserver")


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def registrar_y_activar(c, correo, nick):
    correos = get_email_sender()
    r = c.post("/api/cuentas", json={"correo": correo, "contrasena": "clave123", "confirmacion": "clave123",
                                     "nickname": nick, "acepta_terminos": True})
    ok(r.status_code == 201, f"registro {nick}: {r.json()}")
    token = correos.enviados[-1].enlace.split("token=")[1]
    r = c.post("/api/sesiones", json={"correo": correo, "contrasena": "clave123"})
    ok(r.status_code == 403 and r.json()["codigo"] == "cuenta_no_activada", "pendiente no inicia sesión")
    ok(c.post("/api/cuentas/activar", json={"token": token}).status_code == 200, f"activar {nick}")
    ok(c.post("/api/cuentas/activar", json={"token": token}).status_code == 410, "token de un solo uso")
    r = c.post("/api/sesiones", json={"correo": correo.upper(), "contrasena": "clave123"})
    ok(r.status_code == 200 and r.json() == {"nickname": nick}, f"login {nick}")


def test_flujo_completo(db):
    correos = get_email_sender()
    with cliente() as a, cliente() as b, cliente() as x:
        ok("uq_accounts_nickname" in db.accounts.index_information(), "índices del Entregable 2 creados")
        registrar_y_activar(a, "ana@unas.edu.pe", "ana_07")
        registrar_y_activar(b, "beto@unas.edu.pe", "beto")
        registrar_y_activar(x, "intruso@unas.edu.pe", "intruso")
        r = a.post("/api/cuentas", json={"correo": "otra@unas.edu.pe", "contrasena": "clave123",
                                         "confirmacion": "clave123", "nickname": "ANA_07", "acepta_terminos": True})
        ok(r.status_code == 409, "nickname único sin mayúsculas (colación)")
        cuenta = db.accounts.find_one({"email": "ana@unas.edu.pe"})
        ok(cuenta["passwordHash"].startswith("$2b$12$") and "clave123" not in str(cuenta), "solo hash en BD")

        r = a.post("/api/publicaciones", json={"tipo": "OFREZCO", "titulo": "Apuntes de cálculo",
                                               "descripcion": "Los presto", "duracion": 3})
        ok(r.status_code == 201, "crear publicación")
        pid = r.json()["id"]
        ok(r.json()["segundos_restantes"] == 86400, "duración fija 24 h")
        feed = b.get("/api/feed").json()
        ok(feed["items"][0]["nickname_autor"] == "ana_07" and not feed["items"][0]["es_propia"], "feed ajeno")
        ok("ana@unas.edu.pe" not in str(feed), "correo no expuesto en el feed")
        ok(b.get("/api/feed?tipo=NECESITO").json()["mensaje_vacio"].startswith("No hay publicaciones de este tipo"),
           "filtro por tipo")
        ok(a.get("/api/feed").json()["items"][0]["es_propia"], "Tu publicación")
        ok(a.get("/api/publicaciones/cupo").json() == {"activas": 1, "maximo": 3}, "cupo")
        ok(len(a.get("/api/publicaciones/mias").json()["items"]) == 1, "mis publicaciones")

        r = b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "¿Me los prestas?"})
        ok(r.status_code == 201, "responder (chat + primer mensaje en transacción)")
        cid = r.json()["chat_id"]
        r = b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "otra vez"})
        ok(r.status_code == 409 and r.json()["chat_id"] == cid, "un chat por usuario/publicación")
        ok(a.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "yo"}).status_code == 403, "no a la propia")
        ok(b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "x"},
                  files={"imagen": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")}).status_code == 422, "texto o imagen")

        lista = a.get("/api/chats").json()["items"]
        ok(lista[0]["no_leidos"] and lista[0]["nickname_contraparte"] == "beto", "mis chats con no leídos")
        detalle = a.get(f"/api/chats/{cid}").json()
        ok(detalle["mensajes"][0]["texto"] == "¿Me los prestas?" and not detalle["aviso"]["activo"], "abrir chat")
        ok(not a.get("/api/chats").json()["items"][0]["no_leidos"], "marcado como leído")
        buf = io.BytesIO()
        img = Image.new("RGB", (4, 4), "red")
        exif = img.getexif()
        exif[0x010F] = "CamaraEspia"
        img.save(buf, format="JPEG", exif=exif)
        r = a.post(f"/api/chats/{cid}/mensajes", files={"imagen": ("foto.jpg", buf.getvalue(), "image/jpeg")})
        ok(r.status_code == 201 and r.json()["imagen_url"], "enviar imagen")
        url = r.json()["imagen_url"]
        img_b = b.get(url)
        ok(img_b.status_code == 200 and img_b.headers["content-type"] == "image/jpeg"
           and b"CamaraEspia" not in img_b.content, "imagen al participante sin EXIF")
        ok(x.get(url).status_code == 404 and x.get(f"/api/chats/{cid}").status_code == 404, "tercero no accede")
        ok(cliente().get(url).status_code == 401, "sin sesión no accede")
        nuevos = b.get(f"/api/chats/{cid}", params={"despues_de": detalle["mensajes"][0]["fecha_envio"]},
                       headers={"X-Actualizacion-Automatica": "1"}).json()["mensajes"]
        ok(len(nuevos) == 1 and nuevos[0]["imagen_url"] == url, "sondeo incremental")

        ok(b.post(f"/api/chats/{cid}/reportes", json={"codigo_motivo": "SPAM"}).status_code == 201, "reportar chat")
        rep = db.reports.find_one({"targetType": "CHAT"})
        ok(len(rep["reportedContentSnapshot"]["retainedImageKeys"]) == 1, "snapshot con imagen retenida")
        ok(a.post(f"/api/publicaciones/{pid}/reportes", json={"codigo_motivo": "SPAM"}).status_code == 403,
           "no reportar la propia")
        ok(b.post(f"/api/publicaciones/{pid}/reportes", json={"codigo_motivo": "FRAUD", "observacion": " x "})
           .status_code == 201, "reportar publicación")
        ok(b.post(f"/api/publicaciones/{pid}/reportes", json={"codigo_motivo": "FRAUD"}).status_code == 409,
           "reporte duplicado")

        ok(a.patch("/api/cuentas/me/nickname", json={"nickname": "ana_nueva"}).status_code == 200, "editar nickname")
        ok(b.get("/api/chats").json()["items"][0]["nickname_contraparte"] == "ana_nueva", "nickname propagado al chat")
        ok(b.get("/api/feed").json()["items"][0]["nickname_autor"] == "ana_nueva", "nickname propagado al feed")

        ok(a.post(f"/api/publicaciones/{pid}/cerrar").status_code == 204, "cerrar publicación")
        ok(b.get(f"/api/publicaciones/{pid}").status_code == 410, "detalle no disponible")
        ok(b.get("/api/feed").json()["mensaje_vacio"] == "No hay publicaciones activas en este momento", "feed vacío")
        ok(b.get(f"/api/chats/{cid}").status_code == 200, "el chat sigue tras cerrar la publicación")

        for i in range(25):
            a.post("/api/publicaciones", json={"tipo": "ACTIVIDAD", "titulo": f"p{i}", "descripcion": "d"}) \
                if i < 2 else b.post("/api/publicaciones", json={"tipo": "ACTIVIDAD", "titulo": f"p{i}", "descripcion": "d"})
        ok(b.post("/api/publicaciones", json={"tipo": "ACTIVIDAD", "titulo": "t", "descripcion": "d"}).status_code == 409,
           "límite de 3 activas")
        cron = {"Authorization": "Bearer s3cr3t"}
        for ruta in ("/jobs/ea03-limpiar-chats-expirados", "/jobs/ea05-depurar-contenido-reportado",
                     "/jobs/ea07-eliminar-cuentas-no-activadas"):
            ok(cliente().get(ruta, headers=cron).status_code == 200 and cliente().get(ruta).status_code == 401, ruta)

        for _ in range(5):
            x.post("/api/sesiones", json={"correo": "nadie@unas.edu.pe", "contrasena": "mala1234"})
        r = x.post("/api/sesiones", json={"correo": "nadie@unas.edu.pe", "contrasena": "mala1234"})
        ok(r.status_code == 429 and "15 min" in r.json()["detail"], "bloqueo por intentos (login_attempts)")

        ok(a.post("/api/contrasena/recuperar", json={"correo": "ana@unas.edu.pe"}).status_code == 202, "recuperar")
        token = correos.enviados[-1].enlace.split("token=")[1]
        ok(a.post("/api/contrasena/restablecer", json={"token": token, "contrasena": "nueva1234",
                                                       "confirmacion": "nueva1234"}).status_code == 200, "restablecer")
        ok(a.get("/api/chats").status_code == 401, "sesiones cerradas al restablecer")
        ok(a.post("/api/sesiones", json={"correo": "ana@unas.edu.pe", "contrasena": "nueva1234"}).status_code == 200,
           "login con nueva contraseña")
        ok(a.get("/feed").status_code == 200 and "@ana_nueva" in a.get("/feed").text, "página del feed")
        ok(a.post("/api/sesiones/cerrar").status_code == 204 and a.get("/api/feed").status_code == 401, "cerrar sesión")


def test_feed_paginado_y_jobs(db):
    ahora = datetime.now(timezone.utc)
    with TestClient(app, base_url="https://testserver") as c:
        ok(c.post("/api/sesiones", json={"correo": "intruso@unas.edu.pe", "contrasena": "clave123"}).status_code == 200,
           "login")
        autor = ObjectId()
        base = ahora - timedelta(hours=1)
        # 45 publicaciones; 5 comparten el mismo instante para probar el desempate por _id
        docs = [{"authorId": autor, "authorNickname": "masivo", "type": "NECESITO" if i % 2 else "OFREZCO",
                 "title": f"m{i:02d}", "description": "d", "createdAt": base + timedelta(seconds=min(i, 40)),
                 "expiresAt": base + timedelta(hours=24), "closedAt": None, "status": "ACTIVE"} for i in range(45)]
        db.publications.delete_many({})
        db.publications.insert_many(docs)
        vistos, cursor, bloques = [], None, 0
        while True:
            r = c.get("/api/feed", params={"cursor": cursor} if cursor else {}).json()
            vistos += [i["titulo"] for i in r["items"]]
            bloques += 1
            cursor = r["siguiente_cursor"]
            if not cursor:
                break
        ok(bloques == 3 and len(vistos) == 45 and len(set(vistos)) == 45, f"feed paginado sin duplicados ({bloques} bloques)")
        ok(vistos[:5] == ["m44", "m43", "m42", "m41", "m40"], "orden descendente con desempate por registro")
        filtrados = c.get("/api/feed", params={"tipo": "NECESITO"}).json()
        ok(all(i["tipo"] == "NECESITO" for i in filtrados["items"]) and filtrados["siguiente_cursor"], "filtro + bloque")
        db.publications.update_many({"title": {"$in": ["m44", "m43"]}}, {"$set": {"expiresAt": ahora - timedelta(seconds=1)}})
        ok(c.get("/api/feed").json()["items"][0]["titulo"] == "m42", "EA-02: vencidas excluidas al consultar")
        ok(c.get("/api/feed", params={"cursor": "basura"}).status_code == 422, "cursor inválido")

        # EA-03: chat expirado con imagen
        almacen = get_image_storage()
        buf = io.BytesIO()
        Image.new("RGB", (4, 4)).save(buf, format="PNG")
        clave = asyncio.run(almacen.guardar(buf.getvalue(), "image/png"))
        copia = asyncio.run(almacen.copiar_a_retencion(clave))
        chat = db.chats.find_one()
        db.messages.delete_many({"chatId": chat["_id"], "imageAttachment": {"$ne": None}})
        db.messages.insert_one({"chatId": chat["_id"], "senderId": chat["authorId"], "senderNickname": "x", "text": None,
                                "imageAttachment": {"objectKey": clave, "mimeType": "image/png", "sizeBytes": 9},
                                "sentAt": ahora})
        db.reports.update_one({"targetType": "CHAT"}, {"$set": {"reportedContentSnapshot.retainedImageKeys": [copia]}})
        db.chats.update_one({"_id": chat["_id"]}, {"$set": {"expiresAt": ahora - timedelta(minutes=1)}})
        ok(c.get(f"/api/chats/{chat['_id']}").status_code in (404, 410), "chat expirado inaccesible al consultar")
        r = c.get("/jobs/ea03-limpiar-chats-expirados", headers=cron).json()
        ok(r["chats_eliminados"] == 1 and db.messages.count_documents({"chatId": chat["_id"]}) == 0, f"EA-03 {r}")
        retenidas = [k for d in db.reports.find() for k in d["reportedContentSnapshot"]["retainedImageKeys"]]
        ok(all(k in almacen.objetos for k in retenidas) and r["imagenes_eliminadas"] == 1,
           "imagen original borrada, copia retenida intacta")

        # EA-05: reportes vencidos
        db.reports.update_many({}, {"$set": {"retentionEndsAt": ahora - timedelta(minutes=1)}})
        r = c.get("/jobs/ea05-depurar-contenido-reportado", headers=cron).json()
        ok(r["reportes_eliminados"] == 2 and db.reports.count_documents({}) == 0
           and not any(k in almacen.objetos for k in retenidas), f"EA-05 {r}")

        # EA-07: cuenta pendiente con 72 h
        c.post("/api/cuentas", json={"correo": "tarde@unas.edu.pe", "contrasena": "clave123",
                                     "confirmacion": "clave123", "nickname": "tarde", "acepta_terminos": True})
        # cuenta con reenvío a las 71 h 59 min: su enlace vence 95 h 59 min después del registro
        # (se registran ambas antes de envejecerlas: cada registro purga las vencidas, RN-43)
        c.post("/api/cuentas", json={"correo": "reenvio@unas.edu.pe", "contrasena": "clave123",
                                     "confirmacion": "clave123", "nickname": "reenvio", "acepta_terminos": True})
        db.accounts.update_one({"email": "tarde@unas.edu.pe"}, {"$set": {"createdAt": ahora - timedelta(hours=72)}})
        db.accounts.update_one({"email": "reenvio@unas.edu.pe"},
                               {"$set": {"createdAt": ahora - timedelta(hours=72, minutes=1),
                                         "activation.expiresAt": ahora + timedelta(hours=23, minutes=58)}})
        from app.jobs.ea07_eliminar_cuentas_no_activadas.repository import INDICE, filtro_no_activadas

        plan = db.accounts.find(filtro_no_activadas(datetime.now(timezone.utc) - timedelta(hours=72))) \
            .hint(INDICE).explain()["queryPlanner"]["winningPlan"]
        ok(INDICE in str(plan) and "IXSCAN" in str(plan), f"EA-07 recorre {INDICE}: {plan}")
        r = c.get("/jobs/ea07-eliminar-cuentas-no-activadas", headers=cron).json()
        ok(r["cuentas_eliminadas"] == 2 and not db.accounts.find_one({"email": {"$in": ["tarde@unas.edu.pe",
                                                                                   "reenvio@unas.edu.pe"]}}),
           f"EA-07 {r}")
        ok(db.accounts.count_documents({"status": "ACTIVA"}) == 3, "cuentas activas intactas")

        # CU-15 registra en system_parameters
        from app.features.m06_configuracion.cu15_configurar_parametros import endpoint as cu15

        ok(cu15.main(["--registrar"]) == 0 and db.system_parameters.count_documents({}) == 5, "CU-15 system_parameters")
