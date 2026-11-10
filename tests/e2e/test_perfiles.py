"""Perfiles de punta a punta contra MongoDB real (SRS v2.0, Fase 2). Ejecutar con `pytest -m e2e`."""
import io

import pytest
from PIL import Image

from app.shared.storage.image_storage import get_image_storage
from tests.e2e.test_flujo_completo import cliente, registrar_y_activar


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def jpeg_con_gps() -> bytes:
    exif = Image.Exif()
    exif[0x8825] = {2: (12, 3, 4)}
    salida = io.BytesIO()
    Image.new("RGB", (900, 600), (10, 120, 200)).save(salida, format="JPEG", exif=exif)
    return salida.getvalue()


def test_perfil_foto_avatar_y_apariencia_en_feed_detalle_y_chat(db):
    with cliente() as a, cliente() as b:
        registrar_y_activar(a, "perfil_a@unas.edu.pe", "perfil_a")
        registrar_y_activar(b, "perfil_b@unas.edu.pe", "perfil_b")

        r = a.get("/api/cuentas/me/perfil")
        assert r.status_code == 200 and r.json()["apariencia"]["tipo"] == "iniciales"
        r = a.patch("/api/cuentas/me/perfil", json={"biografia": "Hola, curso Sistemas", "avatar": "avatar-06"})
        assert r.status_code == 200 and r.json()["apariencia"]["url"] == "/static/avatares/avatar-06.svg"
        r = a.patch("/api/cuentas/me/perfil", json={"biografia": "x" * 161})
        assert r.status_code == 422
        r = a.patch("/api/cuentas/me/perfil", json={"avatar": "mujer"})
        assert r.status_code == 422

        doc = db.accounts.find_one({"nickname": "perfil_a"})
        assert doc["bio"] == "Hola, curso Sistemas" and doc["avatar"] == "avatar-06"
        assert not {"gender", "genero", "avatarGroup"} & set(doc)

        # Foto: ≤ 2 MB, cuadrada, sin EXIF
        r = a.put("/api/cuentas/me/foto", files={"foto": ("yo.jpg", jpeg_con_gps(), "image/jpeg")})
        assert r.status_code == 200, r.text
        url = r.json()["apariencia"]["url"]
        assert url.startswith("/api/perfiles/perfil_a/foto?v=")
        r = a.put("/api/cuentas/me/foto", files={"foto": ("grande.jpg", b"\xff\xd8\xff" + b"0" * (2 * 1024 * 1024),
                                                          "image/jpeg")})
        assert r.status_code == 422 and r.json()["codigo"] == "foto_grande"
        r = a.put("/api/cuentas/me/foto", files={"foto": ("virus.jpg", b"MZ\x90\x00" + b"\x00" * 64, "image/jpeg")})
        assert r.status_code == 422 and r.json()["codigo"] == "foto_formato"

        r = b.get(url)
        assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
        assert r.headers["x-content-type-options"] == "nosniff"
        with Image.open(io.BytesIO(r.content)) as foto:
            assert foto.size == (512, 512) and not foto.getexif()

        # Perfil público: sin correo; requiere sesión
        r = b.get("/api/perfiles/PERFIL_A")
        cuerpo = r.json()
        assert r.status_code == 200 and cuerpo["biografia"] == "Hola, curso Sistemas" and not cuerpo["es_propio"]
        assert "@unas.edu.pe" not in r.text and "correo" not in r.text
        assert b.get("/api/perfiles/nadie").status_code == 404
        with cliente() as anonimo:
            assert anonimo.get("/api/perfiles/perfil_a").status_code == 401
            assert anonimo.get(url).status_code == 401
        assert b.get("/perfiles/perfil_a").status_code == 200

        # Feed, detalle y chat muestran la foto de quien publica / responde
        r = a.post("/api/publicaciones", json={"tipo": "OFREZCO", "titulo": "Apuntes", "descripcion": "De cálculo"})
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        item = next(i for i in b.get("/api/feed").json()["items"] if i["id"] == pid)
        assert item["apariencia_autor"]["tipo"] == "foto"
        assert b.get(f"/api/publicaciones/{pid}").json()["apariencia_autor"]["url"] == url
        r = b.post(f"/api/publicaciones/{pid}/respuestas", data={"texto": "¡Me interesa!"})
        assert r.status_code == 201, r.text
        chat_id = r.json()["chat_id"]
        assert b.get("/api/chats").json()["items"][0]["apariencia_contraparte"]["tipo"] == "foto"
        assert a.get(f"/api/chats/{chat_id}").json()["apariencia_contraparte"]["tipo"] == "iniciales"

        # Quitar la foto la borra del almacenamiento y vuelve al avatar elegido
        clave = db.accounts.find_one({"nickname": "perfil_a"})["photo"]["objectKey"]
        r = a.delete("/api/cuentas/me/foto")
        assert r.status_code == 200 and r.json()["apariencia"]["tipo"] == "avatar"
        assert db.accounts.find_one({"nickname": "perfil_a"})["photo"] is None
        assert clave not in get_image_storage().objetos
