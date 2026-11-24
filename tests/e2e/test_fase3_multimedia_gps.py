"""Fase 3 contra MongoDB real: audio por el chat (con Range) y ubicación en vivo por WebSocket (CU-22)."""
import pytest
from bson import ObjectId
from starlette.websockets import WebSocketDisconnect

from tests.e2e.test_flujo_completo import cliente, registrar_y_activar

OGG = b"OggS\x00\x02" + bytes(range(256)) * 4
ORIGEN = {"origin": "https://testserver"}


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def test_audio_y_ubicacion_en_vivo(db):
    with cliente() as a, cliente() as b, cliente() as x:
        registrar_y_activar(a, "f3_a@unas.edu.pe", "f3_a")
        registrar_y_activar(b, "f3_b@unas.edu.pe", "f3_b")
        registrar_y_activar(x, "f3_x@unas.edu.pe", "f3_x")
        pid = a.post("/api/publicaciones", json={"tipo": "OFREZCO", "titulo": "Música", "descripcion": "x"}).json()["id"]
        chat = b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "Hola"}).json()["chat_id"]

        # Audio: se sube por el campo «audio», se reproduce por rangos y se descarga como adjunto
        r = a.post(f"/api/chats/{chat}/mensajes", files={"audio": ("canción.ogg", OGG, "audio/ogg")})
        assert r.status_code == 201, r.text
        url = r.json()["documento"]["url"]
        assert r.json()["documento"]["tipo"] == "ogg"
        parte = b.get(url, headers={"Range": "bytes=0-3"})
        assert parte.status_code == 206 and parte.content == b"OggS" and parte.headers["content-type"] == "audio/ogg"
        completo = b.get(url)
        assert completo.content == OGG and "attachment" in completo.headers["content-disposition"]
        assert x.get(url).status_code == 404  # un tercero no puede descargarlo
        malo = a.post(f"/api/chats/{chat}/mensajes", files={"audio": ("a.mp3", b"%PDF-1.4", "audio/mpeg")})
        assert malo.status_code == 422 and malo.json()["codigo"] == "audio_invalido"

        # Ubicación en vivo: A comparte, B la recibe; al detener, B recibe «detenido»
        ruta = f"wss://testserver/ws/chats/{chat}/ubicacion"  # cookie Secure: solo viaja por wss
        with a.websocket_connect(ruta, headers=ORIGEN) as wa, b.websocket_connect(ruta, headers=ORIGEN) as wb:
            wa.send_json({"tipo": "posicion", "lat": -9.2963, "lng": -75.9981, "precision": 12})
            recibido = wb.receive_json()
            assert recibido["tipo"] == "posicion" and recibido["nickname"] == "f3_a" and recibido["lat"] == -9.2963
            assert db.live_locations.count_documents({"chatId": ObjectId(chat)}) == 1
            wa.send_json({"tipo": "posicion", "lat": 200, "lng": 0, "precision": 1})
            assert wa.receive_json() == {"tipo": "error", "mensaje": "La ubicación no es válida"}
            wa.send_json({"tipo": "detener"})
            assert wb.receive_json() == {"tipo": "detenido"}
            assert db.live_locations.count_documents({"chatId": ObjectId(chat)}) == 0

        # Al cerrar la conexión se borra lo compartido
        with a.websocket_connect(ruta, headers=ORIGEN) as wa:
            wa.send_json({"tipo": "posicion", "lat": -9.3, "lng": -76.0, "precision": 5})
            wa.send_json({"tipo": "nada"})
            wa.receive_json()  # garantiza que la posición ya se procesó
        assert db.live_locations.count_documents({"chatId": ObjectId(chat)}) == 0

        # Sin acceso: un tercero, otro sitio (Origin) o sin sesión
        for c, cabeceras, codigo in ((x, ORIGEN, 4404), (a, {"origin": "https://malo.example"}, 4401)):
            with pytest.raises(WebSocketDisconnect) as cierre:
                with c.websocket_connect(ruta, headers=cabeceras) as w:
                    w.receive_json()
            assert cierre.value.code == codigo
        with cliente() as anonimo, pytest.raises(WebSocketDisconnect) as cierre:
            with anonimo.websocket_connect(ruta, headers=ORIGEN) as w:
                w.receive_json()
        assert cierre.value.code == 4401
