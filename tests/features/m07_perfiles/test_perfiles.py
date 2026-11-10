"""M07 — Perfiles (SRS v2.0, cambios 2.1–2.4): CU-19 editar mi perfil y CU-20 ver un perfil."""
import asyncio
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from app.features.m03_feed.cu08_consultar_feed.handler import ConsultarFeedHandler
from app.features.m03_feed.cu08_consultar_feed.request import ConsultarFeedRequest
from app.features.m07_perfiles.cu19_editar_perfil.handler import EditarPerfilHandler
from app.features.m07_perfiles.cu19_editar_perfil.request import EditarPerfilRequest
from app.features.m07_perfiles.cu20_ver_perfil.handler import VerPerfilHandler
from app.shared.domain.entities import EstadoCuenta, Estudiante
from app.shared.domain.errors import ErrorValidacion, NoEncontrado
from app.shared.domain.perfiles import (AVATARES, GRUPOS_AVATAR, TAMANO_MAX_FOTO, apariencia, apariencias, color_de,
                                        iniciales)
from tests.fakes import FakeAccountRepository, FakeClock, FakeImageStorage, estudiante

RAIZ = Path(__file__).resolve().parents[3]


def correr(c):
    return asyncio.run(c)


def imagen(formato="JPEG", tamano=(800, 400), exif=True) -> bytes:
    img = Image.new("RGB", tamano, (200, 30, 30))
    salida = io.BytesIO()
    opciones = {}
    if exif and formato == "JPEG":
        datos = Image.Exif()
        datos[0x010F] = "Fabricante"   # Make
        datos[0x8825] = {2: (12, 3, 4)}  # GPSInfo
        opciones["exif"] = datos
    img.save(salida, format=formato, **opciones)
    return salida.getvalue()


def escenario():
    cuentas, fotos, reloj = FakeAccountRepository(), FakeImageStorage(), FakeClock()
    ana = correr(cuentas.crear(estudiante(fecha_activacion=datetime(2026, 10, 2, tzinfo=timezone.utc))))
    beto = correr(cuentas.crear(estudiante(correo="beto@unas.edu.pe", nickname="beto")))
    return EditarPerfilHandler(cuentas, fotos, reloj), VerPerfilHandler(cuentas, fotos), cuentas, fotos, ana, beto


# --- Dominio --------------------------------------------------------------------------------------------------
def test_catalogo_de_12_avatares_en_tres_grupos_y_archivos_existentes():
    assert set(GRUPOS_AVATAR) == {"hombre", "mujer", "neutro"}
    assert all(len(g) == 4 for g in GRUPOS_AVATAR.values()) and len(AVATARES) == 12 == len(set(AVATARES))
    for a in AVATARES:
        svg = (RAIZ / "web/static/avatares" / f"{a}.svg").read_text(encoding="utf-8")
        assert svg.startswith("<svg") and "<script" not in svg and "href" not in svg  # SVG propio, sin enlaces


@pytest.mark.parametrize("nickname, esperado", [("ana_07", "A0"), ("ana", "AN"), ("BetoRuiz", "BR"), ("x", "X"),
                                                ("maria.lopez", "ML"), ("__", "?")])
def test_iniciales(nickname, esperado):
    assert iniciales(nickname) == esperado


def test_color_de_iniciales_deriva_del_id_no_de_datos_personales():
    assert all(1 <= color_de(str(i)) <= 6 for i in range(200))
    assert color_de("abc") == color_de("abc")
    assert len({color_de(str(i)) for i in range(200)}) == 6


def test_apariencia_prioriza_foto_luego_avatar_luego_iniciales():
    from app.shared.domain.perfiles import FotoPerfil

    foto = FotoPerfil("perfiles/x.webp", "image/webp", datetime(2026, 11, 1, tzinfo=timezone.utc))
    assert apariencia("1", "ana", foto, "avatar-03").tipo == "foto"
    assert apariencia("1", "ana", foto).url.startswith("/api/perfiles/ana/foto?v=")
    assert apariencia("1", "ana", None, "avatar-03").url == "/static/avatares/avatar-03.svg"
    sin = apariencia("1", "ana", None, "avatar-99")  # un id desconocido no se usa
    assert sin.tipo == "iniciales" and sin.url is None and sin.iniciales == "AN"


def test_no_se_guarda_ni_se_infiere_genero():
    """Cambio 2.3: la entidad no tiene ningún campo de género ni de grupo de avatar."""
    campos = {f for f in Estudiante.__dataclass_fields__}
    assert not campos & {"genero", "sexo", "grupo_avatar"}
    from app.shared.db.mapeo import estudiante_a_doc
    doc = estudiante_a_doc(estudiante(avatar="avatar-05"))
    assert doc["avatar"] == "avatar-05" and not {"gender", "genero", "avatarGroup"} & set(doc)


# --- CU-19 ----------------------------------------------------------------------------------------------------
def test_biografia_max_160_y_espacios_normalizados():
    assert EditarPerfilRequest(biografia="  hola\n\nmundo  ").biografia == "hola mundo"
    assert len(EditarPerfilRequest(biografia="a" * 160).biografia) == 160
    with pytest.raises(ValidationError):
        EditarPerfilRequest(biografia="a" * 161)


def test_avatar_debe_ser_del_catalogo():
    assert EditarPerfilRequest(avatar="avatar-12").avatar == "avatar-12"
    assert EditarPerfilRequest(avatar="").avatar is None
    for malo in ("avatar-13", "../x", "hombre"):
        with pytest.raises(ValidationError):
            EditarPerfilRequest(avatar=malo)


def test_editar_biografia_y_avatar():
    editar, _, cuentas, _, ana, _ = escenario()
    r = correr(editar.actualizar(ana, EditarPerfilRequest(biografia="Estudio sistemas", avatar="avatar-07")))
    assert r.biografia == "Estudio sistemas" and r.avatar == "avatar-07" and r.apariencia.tipo == "avatar"
    assert r.fecha_ingreso == datetime(2026, 10, 2, tzinfo=timezone.utc)  # fecha de activación
    assert "correo" not in json.dumps(r.model_dump(mode="json"))
    r = correr(editar.actualizar(ana, EditarPerfilRequest(biografia="", avatar=None)))
    assert r.apariencia.tipo == "iniciales" and r.apariencia.iniciales == "A0"


def test_foto_recortada_cuadrada_sin_exif_y_reemplaza_la_anterior():
    editar, _, cuentas, fotos, ana, _ = escenario()
    r = correr(editar.subir_foto(ana, imagen()))
    assert r.tiene_foto and r.apariencia.tipo == "foto"
    primera = cuentas.cuentas[ana].foto.referencia
    assert primera.startswith("perfiles/") and primera.endswith(".webp")
    with Image.open(io.BytesIO(fotos.objetos[primera])) as guardada:
        assert guardada.format == "WEBP" and guardada.size == (400, 400)  # cuadrado; no se agranda
        assert not guardada.getexif() and "exif" not in guardada.info
    correr(editar.subir_foto(ana, imagen("PNG", (1200, 900))))
    segunda = cuentas.cuentas[ana].foto.referencia
    assert primera not in fotos.objetos and segunda in fotos.objetos
    with Image.open(io.BytesIO(fotos.objetos[segunda])) as guardada:
        assert guardada.size == (512, 512)
    r = correr(editar.quitar_foto(ana))
    assert not r.tiene_foto and segunda not in fotos.objetos and cuentas.cuentas[ana].foto is None


@pytest.mark.parametrize("contenido, codigo", [
    (b"", "foto_vacia"),
    (b"GIF89a" + b"\0" * 100, "foto_formato"),
    (b"MZ\x90\0" + b"\0" * 100, "foto_formato"),
    (b"\xff\xd8\xff" + b"\0" * 100, "foto_invalida"),  # firma JPEG pero contenido dañado
    (b"\xff\xd8\xff" + b"\0" * TAMANO_MAX_FOTO, "foto_grande"),
])
def test_foto_rechazada(contenido, codigo):
    editar, _, cuentas, fotos, ana, _ = escenario()
    with pytest.raises(ErrorValidacion) as error:
        correr(editar.subir_foto(ana, contenido))
    assert error.value.codigo == codigo and error.value.extra.get("campo") == "foto"
    assert cuentas.cuentas[ana].foto is None and not fotos.objetos


# --- CU-20 ----------------------------------------------------------------------------------------------------
def test_ver_perfil_publico_sin_correo():
    editar, ver, _, _, ana, beto = escenario()
    correr(editar.actualizar(ana, EditarPerfilRequest(biografia="Hola", avatar="avatar-10")))
    p = correr(ver.handle(beto, "ANA_07"))  # sin distinguir mayúsculas
    assert p.nickname == "ana_07" and p.biografia == "Hola" and not p.es_propio
    assert p.apariencia.url == "/static/avatares/avatar-10.svg"
    assert "@unas.edu.pe" not in p.model_dump_json()
    assert correr(ver.handle(ana, "ana_07")).es_propio


def test_perfil_de_cuenta_pendiente_o_inexistente_no_existe():
    _, ver, cuentas, _, ana, _ = escenario()
    correr(cuentas.crear(estudiante(correo="pend@unas.edu.pe", nickname="pendiente",
                                    estado=EstadoCuenta.PENDIENTE_ACTIVACION)))
    for nick in ("pendiente", "nadie"):
        with pytest.raises(NoEncontrado):
            correr(ver.handle(ana, nick))


def test_foto_publica_se_descarga_y_sin_foto_es_404():
    editar, ver, _, _, ana, beto = escenario()
    with pytest.raises(NoEncontrado):
        correr(ver.foto("ana_07"))
    correr(editar.subir_foto(ana, imagen()))
    descarga = correr(ver.foto("ana_07"))
    assert descarga.mime_type == "image/webp" and descarga.contenido.startswith(b"RIFF")


# --- Cambio 2.4: feed con foto/avatar -------------------------------------------------------------------------
def test_apariencias_en_lote_y_sin_repositorio_usa_iniciales():
    editar, _, cuentas, _, ana, beto = escenario()
    correr(editar.actualizar(ana, EditarPerfilRequest(avatar="avatar-01")))
    caras = correr(apariencias(cuentas, {ana: "ana_07", beto: "beto", "fantasma": "ido"}))
    assert caras[ana].tipo == "avatar" and caras[beto].tipo == "iniciales" and caras["fantasma"].iniciales == "ID"
    assert correr(apariencias(None, {ana: "ana_07"}))[ana].tipo == "iniciales"


def test_feed_incluye_la_apariencia_del_autor():
    from datetime import timedelta

    from app.shared.domain.entities import Publicacion, TipoPublicacion
    from tests.fakes import FakePublicationRepository

    editar, _, cuentas, _, ana, beto = escenario()
    correr(editar.actualizar(ana, EditarPerfilRequest(avatar="avatar-02")))
    pubs, reloj = FakePublicationRepository(), FakeClock()
    ahora = reloj.ahora()
    correr(pubs.crear(Publicacion("", ana, "ana_07", TipoPublicacion.OFREZCO, "t", "d", ahora,
                                  ahora + timedelta(hours=24))))
    r = correr(ConsultarFeedHandler(pubs, reloj, cuentas).handle(beto, ConsultarFeedRequest()))
    assert r.items[0].apariencia_autor.url == "/static/avatares/avatar-02.svg"
