"""Fase 4 contra MongoDB real: videollamada (cola y señales en Mongo) y reporte."""
import pytest
from bson import ObjectId
from starlette.websockets import WebSocketDisconnect

from tests.e2e.test_flujo_completo import cliente, registrar_y_activar

ORIGEN = {"origin": "https://testserver"}
RUTA = "wss://testserver/ws/videollamada"  # cookie Secure: solo viaja por wss


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def _esperar(ws, tipo):
    """Lee mensajes hasta el del tipo pedido (el servidor puede mandar «esperando» antes)."""
    for _ in range(20):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó {tipo}")


def test_videollamada_entre_dos_estudiantes(db):
    with cliente() as a, cliente() as b, cliente() as sin_perfil:
        registrar_y_activar(a, "vc_a@unas.edu.pe", "vc_a")
        registrar_y_activar(b, "vc_b@unas.edu.pe", "vc_b")
        registrar_y_activar(sin_perfil, "vc_c@unas.edu.pe", "vc_c")
        assert a.patch("/api/cuentas/me/identidad", json={"nombre": "Ana Ríos", "carrera": "Agronomía"}).status_code == 200
        assert b.patch("/api/cuentas/me/identidad", json={"nombre": "Beto Paz", "carrera": "Zootecnia"}).json()["carrera"] == "Zootecnia"
        assert a.get("/videollamada").status_code == 200 and "Empezar" in a.get("/videollamada").text
        assert "Completar mi perfil" in sin_perfil.get("/videollamada").text

        with a.websocket_connect(RUTA, headers=ORIGEN) as wa, b.websocket_connect(RUTA, headers=ORIGEN) as wb:
            wa.send_json({"tipo": "buscar"})
            assert wa.receive_json() == {"tipo": "esperando"}
            wb.send_json({"tipo": "buscar"})
            para_a, para_b = _esperar(wa, "emparejado"), _esperar(wb, "emparejado")
            assert para_a["sala"] == para_b["sala"] and para_a["iniciador"] != para_b["iniciador"]
            assert para_a["pareja"] == {"nombre": "Beto Paz", "carrera": "Zootecnia", "nickname": "vc_b"}
            sala = para_a["sala"]
            assert db.videocall_queue.count_documents({}) == 0

            # Señal WebRTC y chat de texto pasan por el buzón de la otra persona
            iniciador, otro = (wa, wb) if para_a["iniciador"] else (wb, wa)
            iniciador.send_json({"tipo": "senal", "datos": {"descripcion": {"type": "offer", "sdp": "v=0"}}})
            assert _esperar(otro, "senal")["datos"]["descripcion"]["type"] == "offer"
            otro.send_json({"tipo": "chat", "texto": "¡Hola!"})
            assert _esperar(iniciador, "chat")["texto"] == "¡Hola!"

            # Reporte: el servidor decide a quién (la otra persona de la sala)
            r = b.post("/api/videollamada/reportes", json={"sala_id": sala, "motivo": "SPAM", "detalle": "Publicidad"})
            assert r.status_code == 201, r.text
            reporte = db.videocall_reports.find_one({"_id": ObjectId(r.json()["id"])})
            assert reporte["reason"] == "SPAM" and reporte["status"] == "PENDIENTE"
            assert reporte["reporterId"] != reporte["reportedId"]
            assert sin_perfil.post("/api/videollamada/reportes", json={"sala_id": sala, "motivo": "SPAM"}).status_code == 404

            # Colgar: la otra persona se entera y la sala queda cerrada (sin audio ni video guardado)
            wa.send_json({"tipo": "colgar"})
            assert _esperar(wa, "colgado") == {"tipo": "colgado"}
            assert _esperar(wb, "colgo")["sala"] == sala
            assert db.videocall_rooms.find_one({"_id": ObjectId(sala)})["endedAt"] is not None

        # Sin nombre ni carrera, o desde otro sitio, el WebSocket se cierra
        for c, cabeceras, codigo in ((sin_perfil, ORIGEN, 4403), (a, {"origin": "https://malo.example"}, 4401)):
            with pytest.raises(WebSocketDisconnect) as cierre:
                with c.websocket_connect(RUTA, headers=cabeceras) as w:
                    w.receive_json()
            assert cierre.value.code == codigo
        assert db.videocall_queue.count_documents({}) == 0  # al desconectarse nadie queda en la cola
