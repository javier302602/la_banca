"""Datos de demostración para un despliegue de La Banca (SRS v2.0, Fase 7).

Crea 4 cuentas activas, cada una con su avatar elegido y biografía; publicaciones con imágenes; y chats con
emojis, stickers, una imagen y documentos (PDF, DOCX y TXT). Todo pasa por los casos de uso de la app (mismas
validaciones, imágenes re-codificadas sin EXIF y archivos guardados en el almacenamiento configurado).

Uso (dentro del contenedor de la app):
    docker compose exec app python -m scripts.seed_demo              # crea los datos (falla si ya existen)
    docker compose exec app python -m scripts.seed_demo --reiniciar  # borra antes los datos de demo
Contraseña de las 4 cuentas: la de DEMO_CONTRASENA o, si no está, «Demo1234!». No lo uses con datos reales.
"""
import argparse
import asyncio
import io
import os
import sys
import zipfile

USUARIOS = [  # (nickname, avatar elegido, biografía)
    ("ana_demo", "avatar-06", "Estudio Ingeniería de Sistemas. Siempre con café ☕ y apuntes ordenados."),
    ("beto_demo", "avatar-02", "Agronomía, 5.º ciclo. Juego fútbol los jueves ⚽."),
    ("caro_demo", "avatar-10", "Me gusta enseñar cálculo y organizar grupos de estudio 📚."),
    ("dani_demo", "avatar-04", "Zootecnia. Busco gente para correr por el campus 🏃."),
]


def imagen(fondo, figura, forma="circulo") -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (800, 600), fondo)
    d = ImageDraw.Draw(img)
    if forma == "circulo":
        d.ellipse((250, 150, 550, 450), fill=figura)
    elif forma == "libro":
        d.rectangle((200, 180, 395, 430), fill=figura)
        d.rectangle((405, 180, 600, 430), fill=figura)
        for y in range(220, 410, 30):
            d.line((230, y, 365, y), fill=fondo, width=6)
            d.line((435, y, 570, y), fill=fondo, width=6)
    else:  # calculadora
        d.rounded_rectangle((280, 100, 520, 500), 30, fill=figura)
        d.rectangle((310, 130, 490, 200), fill=fondo)
        for f in range(4):
            for c in range(3):
                d.rounded_rectangle((310 + c * 62, 230 + f * 64, 360 + c * 62, 278 + f * 64), 8, fill=fondo)
    salida = io.BytesIO()
    img.save(salida, format="JPEG", quality=85)
    return salida.getvalue()


def pdf(texto: str) -> bytes:
    contenido = f"BT /F1 18 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1", "replace")
    objetos = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
               b"/Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length %d >>\nstream\n" % len(contenido) + contenido + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    salida, posiciones = io.BytesIO(), []
    salida.write(b"%PDF-1.4\n")
    for i, obj in enumerate(objetos, 1):
        posiciones.append(salida.tell())
        salida.write(b"%d 0 obj\n" % i + obj + b"\nendobj\n")
    xref = salida.tell()
    salida.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1))
    for p in posiciones:
        salida.write(b"%010d 00000 n \n" % p)
    salida.write(b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref))
    return salida.getvalue()


def docx(parrafos: list[str]) -> bytes:
    cuerpo = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in parrafos)
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml",
                    '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                    '<Default Extension="xml" ContentType="application/xml"/>'
                    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                    "</Types>")
        zf.writestr("_rels/.rels",
                    '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                    "</Relationships>")
        zf.writestr("word/document.xml",
                    '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    f"<w:body>{cuerpo}</w:body></w:document>")
    return salida.getvalue()


async def reiniciar(db, nicks: list[str]) -> None:
    from app.shared.storage.image_storage import get_image_storage

    cuentas = [d["_id"] async for d in db.accounts.find({"nickname": {"$in": nicks}}, {"_id": 1})]
    almacen, claves = get_image_storage(), []
    async for p in db.publications.find({"authorId": {"$in": cuentas}}, {"images.objectKey": 1}):
        claves += [i["objectKey"] for i in p.get("images") or []]
    chats = [d["_id"] async for d in db.chats.find({"participants": {"$in": cuentas}}, {"_id": 1})]
    async for m in db.messages.find({"chatId": {"$in": chats}}):
        claves += [m[c]["objectKey"] for c in ("imageAttachment", "documentAttachment") if m.get(c)]
    async for a in db.accounts.find({"_id": {"$in": cuentas}, "photo": {"$ne": None}}, {"photo": 1}):
        claves.append(a["photo"]["objectKey"])
    for clave in claves:
        await almacen.eliminar(clave)
    await db.messages.delete_many({"chatId": {"$in": chats}})
    await db.chats.delete_many({"_id": {"$in": chats}})
    await db.publications.delete_many({"authorId": {"$in": cuentas}})
    await db.sessions.delete_many({"userId": {"$in": cuentas}})
    await db.accounts.delete_many({"_id": {"$in": cuentas}})


async def sembrar(reiniciar_antes: bool) -> None:
    from app.features.m02_publicaciones.cu05_crear_publicacion.handler import CrearPublicacionHandler
    from app.features.m02_publicaciones.cu05_crear_publicacion.repository import MongoCrearPublicacionRepository
    from app.features.m02_publicaciones.cu05_crear_publicacion.request import CrearPublicacionRequest
    from app.features.m04_chat.cu10_responder_publicacion import endpoint as cu10
    from app.features.m04_chat.cu10_responder_publicacion.request import MensajeEntrante as PrimerMensaje
    from app.features.m04_chat.cu11_enviar_mensaje.handler import EnviarMensajeHandler
    from app.features.m04_chat.cu11_enviar_mensaje.repository import MongoEnviarMensajeRepository
    from app.features.m04_chat.cu11_enviar_mensaje.request import MensajeEntrante
    from app.features.m07_perfiles.cu19_editar_perfil.handler import EditarPerfilHandler
    from app.features.m07_perfiles.cu19_editar_perfil.repository import MongoEditarPerfilRepository
    from app.features.m07_perfiles.cu19_editar_perfil.request import EditarPerfilRequest
    from app.shared.clock import get_clock
    from app.shared.config.provider import get_config
    from app.shared.db.migraciones import aplicar_al_arrancar
    from app.shared.db.mongo import base_de_datos
    from app.shared.domain.entities import ClaveParametro
    from app.shared.storage.image_storage import get_image_storage
    from scripts.crear_usuario import crear

    db, almacen, reloj = base_de_datos(), get_image_storage(), get_clock()
    await aplicar_al_arrancar()
    nicks = [n for n, _, _ in USUARIOS]
    if reiniciar_antes:
        await reiniciar(db, nicks)
    elif await db.accounts.count_documents({"nickname": {"$in": nicks}}):
        raise SystemExit("Ya hay datos de demo: usa --reiniciar para crearlos de nuevo")

    dominio = get_config().texto(ClaveParametro.DOMINIO_INSTITUCIONAL)
    clave = os.environ.get("DEMO_CONTRASENA", "Demo1234!")
    ids = {}
    perfiles = EditarPerfilHandler(MongoEditarPerfilRepository(db), almacen, reloj)
    for nick, avatar, bio in USUARIOS:
        ids[nick] = await crear(f"{nick.replace('_', '.')}@{dominio}", nick, clave)
        await perfiles.actualizar(ids[nick], EditarPerfilRequest(biografia=bio, avatar=avatar))
    print(f"4 cuentas: {', '.join('@' + n for n in nicks)} (contraseña: {clave})")

    publicar = CrearPublicacionHandler(MongoCrearPublicacionRepository(db), get_config(), reloj, almacen)
    pubs = {}
    for clave_pub, nick, tipo, titulo, descripcion, imagenes in [
        ("libro", "ana_demo", "OFREZCO", "Presto libro de Cálculo I (Stewart)",
         "Lo tengo libre hasta el viernes. Lo dejo en la biblioteca central 📖.",
         [imagen("#e4defd", "#4f3cc9", "libro"), imagen("#ffe8b3", "#c2410c", "libro")]),
        ("calculadora", "beto_demo", "NECESITO", "Necesito calculadora científica para el examen",
         "Examen de Física a las 3 pm. Te la devuelvo apenas termine 🙏.", [imagen("#cfeedd", "#2f9e63", "calc")]),
        ("estudio", "caro_demo", "ACTIVIDAD", "Grupo de estudio de derivadas",
         "Nos juntamos en el pabellón B, aula 204, de 4 a 6 pm. Traigan ejercicios ✏️.",
         [imagen("#d6e4ff", "#3b6fd8"), imagen("#ffd6d1", "#b02a37"), imagen("#d1f0f5", "#1e4a52")]),
        ("correr", "dani_demo", "ACTIVIDAD", "¿Alguien para correr 5 km hoy?", "Salimos 6 pm desde la puerta principal.", []),
    ]:
        r = await publicar.handle(ids[nick], nick, CrearPublicacionRequest(tipo=tipo, titulo=titulo, descripcion=descripcion),
                                  imagenes)
        pubs[clave_pub] = r.id
    print(f"{len(pubs)} publicaciones (6 imágenes)")

    responder = cu10.get_handler(db)
    enviar = EnviarMensajeHandler(MongoEnviarMensajeRepository(db), almacen, reloj)

    async def chat(pub, quien, primero, *mensajes):
        c = (await responder.handle(ids[quien], quien, pubs[pub], PrimerMensaje(texto=primero))).chat_id
        for nick, contenido in mensajes:
            await enviar.handle(ids[nick], nick, c, MensajeEntrante(**contenido))
        return c

    await chat("libro", "caro_demo", "¡Hola Ana! ¿Todavía tienes el libro? 😊",
               ("ana_demo", {"texto": "¡Sí! Te lo puedo dejar hoy 👍"}),
               ("ana_demo", {"texto": "Te paso también mi resumen del capítulo 3"}),
               ("ana_demo", {"documento": pdf("Resumen - Calculo I - Capitulo 3"), "documento_nombre": "Resumen capítulo 3.pdf"}),
               ("caro_demo", {"sticker": "sticker-06"}),
               ("caro_demo", {"texto": "¡Mil gracias! Nos vemos a las 4 ☕"}))
    await chat("calculadora", "ana_demo", "Beto, tengo una Casio fx-991, ¿te sirve?",
               ("beto_demo", {"texto": "¡Me salvas! 🙌"}),
               ("beto_demo", {"sticker": "sticker-17"}),
               ("ana_demo", {"imagen": imagen("#cfeedd", "#565b6e", "calc")}),
               ("ana_demo", {"texto": "Esta es. Te espero en la cafetería ⏰"}))
    await chat("estudio", "beto_demo", "¡Me apunto al grupo! 📚",
               ("caro_demo", {"texto": "Genial. Aquí está la lista de ejercicios y la guía."}),
               ("caro_demo", {"documento": docx(["Ejercicios de derivadas", "1. Derive f(x) = x^3 + 2x",
                                                 "2. Regla de la cadena: g(x) = sen(x^2)"]),
                              "documento_nombre": "Ejercicios derivadas.docx"}),
               ("caro_demo", {"documento": "Traer: calculadora, cuaderno y muchas ganas 💪\n".encode(),
                              "documento_nombre": "Qué traer.txt"}),
               ("beto_demo", {"sticker": "sticker-20"}))
    print("3 chats con emojis, stickers, una imagen y documentos (PDF, DOCX y TXT)")


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--reiniciar", action="store_true", help="borra antes los datos de demo")
    asyncio.run(sembrar(analizador.parse_args().reiniciar))
    print("Datos de demo listos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
