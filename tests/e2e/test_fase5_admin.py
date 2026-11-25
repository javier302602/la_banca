"""Fase 5 contra MongoDB real: panel de administradores con TODOS los reportes y acciones de moderación."""
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.shared.config import moderacion
from app.shared.email.sender import get_email_sender
from tests.e2e.test_flujo_completo import cliente, cron, registrar_y_activar

ORIGEN = {"origin": "https://testserver"}
RUTA_LLAMADA = "wss://testserver/ws/videollamada"


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def _esperar(ws, tipo):
    for _ in range(20):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(tipo)


def test_panel_de_administradores(db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "adm_jefa@unas.edu.pe")
    monkeypatch.setenv("CRON_SECRET", "s3cr3t")
    moderacion._patrones.cache_clear()
    correos = get_email_sender()
    with cliente() as jefa, cliente() as ana, cliente() as beto:
        registrar_y_activar(jefa, "adm_jefa@unas.edu.pe", "adm_jefa")
        registrar_y_activar(ana, "adm_ana@unas.edu.pe", "adm_ana")
        registrar_y_activar(beto, "adm_beto@unas.edu.pe", "adm_beto")
        for c, nombre in ((ana, "Ana"), (beto, "Beto")):
            assert c.patch("/api/cuentas/me/identidad", json={"nombre": nombre, "carrera": "Agronomía"}).status_code == 200

        # 1) Reportes: publicación (persona), chat (filtro automático) y videollamada
        pid = ana.post("/api/publicaciones", json={"tipo": "OFREZCO", "titulo": "Libros", "descripcion": "Baratos"}).json()["id"]
        enviados = len(correos.enviados)
        assert beto.post(f"/api/publicaciones/{pid}/reportes", json={"codigo_motivo": "SPAM"}).status_code == 201
        assert any(c.destinatario == "adm_jefa@unas.edu.pe" and "Nuevo reporte" in c.asunto
                   for c in correos.enviados[enviados:])  # aviso por correo a los admins
        chat = beto.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "Hola"}).json()["chat_id"]
        # Respuesta a una publicación (CU-10) con una palabra ofensiva: pasa por el filtro y además se reporta
        pid2 = ana.post("/api/publicaciones", json={"tipo": "NECESITO", "titulo": "Tutor", "descripcion": "Cálculo"}).json()["id"]
        respuesta = beto.post(f"/api/publicaciones/{pid2}/respuestas", data={"texto": "Qué estúpida pregunta"})
        assert respuesta.status_code == 201  # el filtro no bloquea
        chat_respuesta = respuesta.json()["chat_id"]
        assert ana.post(f"/api/chats/{chat_respuesta}/reportes", json={"codigo_motivo": "HARASSMENT"}).status_code == 201
        assert ana.post(f"/api/chats/{chat}/mensajes", data={"texto": "Eres un IDIOTA"}).status_code == 201  # no se bloquea
        with ana.websocket_connect(RUTA_LLAMADA, headers=ORIGEN) as wa, beto.websocket_connect(RUTA_LLAMADA, headers=ORIGEN) as wb:
            wa.send_json({"tipo": "buscar"})
            wb.send_json({"tipo": "buscar"})
            sala = _esperar(wa, "emparejado")["sala"]
            _esperar(wb, "emparejado")
            assert beto.post("/api/videollamada/reportes", json={"sala_id": sala, "motivo": "INSULTOS"}).status_code == 201

        # 2) Solo los admins ven el panel
        for ruta in ("/api/admin/reportes", "/api/admin/reportes/pendientes", "/api/admin/historial"):
            assert ana.get(ruta).status_code == 403, ruta
        assert ana.get("/admin", follow_redirects=False).headers["location"] == "/feed"
        assert "Admin" in jefa.get("/feed").text and "Admin" not in ana.get("/feed").text
        panel = jefa.get("/api/admin/reportes").json()
        assert panel["pendientes"] == 5
        assert {r["tipo"] for r in panel["reportes"]} == {"PUBLICACION", "CHAT", "VIDEOLLAMADA"}
        de_respuesta = [r for r in panel["reportes"] if r["objeto_id"] == chat_respuesta]
        assert sorted(r["automatico"] for r in de_respuesta) == [False, True]  # filtro + reporte de Ana
        automatico = next(r for r in de_respuesta if r["automatico"])
        assert "estupida" in automatico["detalle"] and automatico["reportado"]["nickname"] == "adm_beto"
        assert automatico["contenido"]["mensajes"][0]["text"] == "Qué estúpida pregunta"
        assert next(r for r in de_respuesta if not r["automatico"])["reportante"]["nickname"] == "adm_ana"

        # Una cuenta que NO es admin no puede moderar: 403 y el reporte queda igual
        r = ana.post(f"/api/admin/reportes/{automatico['origen']}/{automatico['id']}/acciones", json={"accion": "DESCARTAR"})
        assert r.status_code == 403 and r.json()["codigo"] == "solo_admin"
        assert ana.post(f"/api/admin/reportes/{automatico['origen']}/{automatico['id']}/acciones",
                        json={"accion": "BANEAR"}).status_code == 403
        assert db.reports.find_one({"_id": ObjectId(automatico["id"])}).get("status") == "PENDIENTE"
        for r in de_respuesta:  # se descartan para seguir con el resto de la prueba
            assert jefa.post(f"/api/admin/reportes/{r['origen']}/{r['id']}/acciones", json={"accion": "DESCARTAR"}).status_code == 200
        por_tipo = {r["tipo"]: r for r in panel["reportes"] if r["objeto_id"] != chat_respuesta}
        assert por_tipo["CHAT"]["automatico"] and por_tipo["CHAT"]["reportante"] is None
        assert "idiota" in por_tipo["CHAT"]["detalle"] and por_tipo["CHAT"]["contenido"]["mensajes"][0]["text"] == "Eres un IDIOTA"
        llamada = por_tipo["VIDEOLLAMADA"]
        assert (llamada["reportante"]["nickname"], llamada["reportado"]["nickname"], llamada["motivo"]) == ("adm_beto", "adm_ana", "INSULTOS")
        assert llamada["contenido"]["sala"]["inicio"]  # registro de la sala, sin video
        assert por_tipo["PUBLICACION"]["contenido"]["publicacion"]["title"] == "Libros"

        def accion(r, **cuerpo):
            respuesta = jefa.post(f"/api/admin/reportes/{r['origen']}/{r['id']}/acciones", json=cuerpo)
            assert respuesta.status_code == 200, respuesta.text
            return respuesta.json()

        # 3) Acciones: ocultar la publicación, advertir, descartar, suspender y banear
        assert accion(por_tipo["PUBLICACION"], accion="ELIMINAR_CONTENIDO")["estado"] == "RESUELTO"
        assert db.publications.find_one({"_id": ObjectId(pid)})["status"] == "REMOVED"
        assert all(i["id"] != pid for i in beto.get("/api/feed").json()["items"])
        accion(por_tipo["CHAT"], accion="ADVERTIR", mensaje="Cuida tu lenguaje")
        assert "Cuida tu lenguaje" in ana.get("/feed").text  # banner hasta marcarla como leída
        assert ana.delete("/api/cuentas/me/aviso").status_code == 204 and "Cuida tu lenguaje" not in ana.get("/feed").text
        assert jefa.post(f"/api/admin/reportes/videollamada/{llamada['id']}/acciones",
                         json={"accion": "ELIMINAR_CONTENIDO"}).status_code == 422  # no hay video que borrar
        accion(llamada, accion="SUSPENDER", dias=2)
        assert ana.get("/api/feed").status_code == 401  # sesión cerrada
        r = ana.post("/api/sesiones", json={"correo": "adm_ana@unas.edu.pe", "contrasena": "clave123"})
        assert r.status_code == 403 and "suspendida hasta" in r.json()["detail"]
        accion(llamada, accion="BANEAR")
        assert db.accounts.find_one({"email": "adm_ana@unas.edu.pe"})["banned"] is True
        mia = next(r for r in jefa.get("/api/admin/reportes?todos=true").json()["reportes"] if r["tipo"] == "VIDEOLLAMADA")
        assert [a["action"] for a in mia["acciones"]] == ["SUSPENDER", "BANEAR"]
        assert jefa.post(f"/api/admin/reportes/contenido/{por_tipo['PUBLICACION']['id']}/acciones",
                         json={"accion": "BANEAR"}).status_code == 200  # (Ana ya estaba baneada: idempotente)
        assert jefa.get("/api/admin/reportes/pendientes").json() == {"pendientes": 0}

        # 4) Historial
        historial = jefa.get("/api/admin/historial").json()["acciones"]
        assert [a["accion"] for a in historial][:3] == ["BANEAR", "BANEAR", "SUSPENDER"]
        assert all(a["admin"] == "adm_jefa" for a in historial)

        # 5) EA-05 borra solo los reportes revisados cuyo plazo venció; un pendiente se conserva
        otra = beto.post("/api/publicaciones", json={"tipo": "OFREZCO", "titulo": "Otra", "descripcion": "x"}).json()["id"]
        with cliente() as caro:
            registrar_y_activar(caro, "adm_caro@unas.edu.pe", "adm_caro")
            assert caro.post(f"/api/publicaciones/{otra}/reportes", json={"codigo_motivo": "OTHER"}).status_code == 201
        pasado = datetime.now(timezone.utc) - timedelta(days=1)
        db.reports.update_many({}, {"$set": {"retentionEndsAt": pasado}})
        assert jefa.get("/jobs/ea05-depurar-contenido-reportado", headers=cron).status_code == 200
        quedan = list(db.reports.find({}, {"status": 1}))
        assert len(quedan) == 1 and quedan[0].get("status") in (None, "PENDIENTE")
