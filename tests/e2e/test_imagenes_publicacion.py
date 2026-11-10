"""Imágenes en publicaciones contra MongoDB real (SRS v2.0, Fase 3). Ejecutar con `pytest -m e2e`."""
import io
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from app.shared.storage.image_storage import get_image_storage
from tests.e2e.test_flujo_completo import cliente, cron, registrar_y_activar


@pytest.fixture(scope="module")
def db(base_e2e_limpia):
    return base_e2e_limpia


def jpeg_con_gps(color) -> bytes:
    exif = Image.Exif()
    exif[0x8825] = {2: (12, 3, 4)}
    salida = io.BytesIO()
    Image.new("RGB", (320, 240), color).save(salida, format="JPEG", exif=exif)
    return salida.getvalue()


def test_imagenes_de_publicacion_reporte_y_limpieza(db, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cr3t")
    almacen = get_image_storage()
    with cliente() as a, cliente() as b:
        registrar_y_activar(a, "img_a@unas.edu.pe", "img_a")
        registrar_y_activar(b, "img_b@unas.edu.pe", "img_b")
        archivos = [("imagenes", (f"{i}.jpg", jpeg_con_gps(c), "image/jpeg")) for i, c in enumerate(["red", "blue"])]
        r = a.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "Libro", "descripcion": "De física"},
                   files=archivos)
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        doc = db.publications.find_one({"title": "Libro"})
        claves = [i["objectKey"] for i in doc["images"]]
        assert len(claves) == 2 and all(k.startswith("publicaciones/") for k in claves)
        assert all(i["mimeType"] == "image/jpeg" and i["sizeBytes"] > 0 for i in doc["images"])

        r = b.get(f"/api/publicaciones/{pid}/imagenes/1")
        assert r.status_code == 200 and r.headers["x-content-type-options"] == "nosniff"
        with Image.open(io.BytesIO(r.content)) as img:
            assert not img.getexif()
        assert b.get(f"/api/publicaciones/{pid}/imagenes/2").status_code == 404
        with cliente() as anonimo:
            assert anonimo.get(f"/api/publicaciones/{pid}/imagenes/0").status_code == 401

        # Demasiadas imágenes o una que no lo es: 422 en el campo «imagenes», sin objetos huérfanos
        antes = len(almacen.objetos)
        cuatro = [("imagenes", (f"{i}.jpg", jpeg_con_gps("red"), "image/jpeg")) for i in range(4)]
        r = a.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "x", "descripcion": "y"}, files=cuatro)
        assert r.status_code == 422 and r.json()["campo"] == "imagenes"
        r = a.post("/api/publicaciones", data={"tipo": "OFREZCO", "titulo": "x", "descripcion": "y"},
                   files=[("imagenes", ("x.png", b"MZ\x90\x00" * 20, "image/png"))])
        assert r.status_code == 422 and r.json()["codigo"] == "imagen_invalida"
        assert len(almacen.objetos) == antes

        # Reporte: las imágenes se copian a retención
        assert b.post(f"/api/publicaciones/{pid}/reportes", json={"codigo_motivo": "SPAM"}).status_code == 201
        snapshot = db.reports.find_one({"targetId": doc["_id"]})["reportedContentSnapshot"]
        retenidas = snapshot["retainedImageKeys"]
        assert snapshot["publicationData"]["imageKeys"] == retenidas
        assert len(retenidas) == 2 and all(k.startswith("reports/") and k in almacen.objetos for k in retenidas)

        # EA-03: publicación vencida → sus imágenes se borran; las retenidas siguen
        db.publications.update_one({"_id": doc["_id"]},
                                   {"$set": {"expiresAt": datetime.now(timezone.utc) - timedelta(minutes=1)}})
        r = a.get("/jobs/ea03-limpiar-chats-expirados", headers=cron)
        assert r.status_code == 200 and r.json()["imagenes_de_publicaciones_eliminadas"] == 2, r.json()
        assert db.publications.find_one({"_id": doc["_id"]})["images"] == []
        assert not any(k in almacen.objetos for k in claves) and all(k in almacen.objetos for k in retenidas)
        assert b.get(f"/api/publicaciones/{pid}/imagenes/0").status_code == 410
