"""Migración 001 — datos de la v1.0.0 (SRS v1.9) al esquema de la v2.0.0 (SRS v2.0).

Agrega con su valor neutro los campos nuevos que la v1 no tenía, sin tocar ningún otro dato:

- accounts:     bio = "", avatar = null, photo = null       (perfiles, Fase 2)
- publications: images = []                                  (imágenes en publicaciones, Fase 3)
- messages:     sticker = null, documentAttachment = null    (chat estilo Messenger, Fase 4)

Idempotente: solo actualiza los documentos a los que les falta el campo, así que una segunda ejecución (o la
restauración de un respaldo de v1 sobre una base ya migrada) no cambia nada que ya esté bien. No infiere ningún
avatar ni dato personal: una cuenta de v1 queda con sus iniciales hasta que la persona elija.
"""

DESCRIPCION = "v1 → v2: perfil (bio, avatar, photo), imágenes de publicación y adjuntos del chat"

CAMPOS = {
    "accounts": {"bio": "", "avatar": None, "photo": None},
    "publications": {"images": []},
    "messages": {"sticker": None, "documentAttachment": None},
}


async def aplicar(db) -> dict:
    resumen = {}
    for coleccion, campos in CAMPOS.items():
        for campo, valor in campos.items():
            r = await db[coleccion].update_many({campo: {"$exists": False}}, {"$set": {campo: valor}})
            resumen[f"{coleccion}.{campo}"] = r.modified_count
    return resumen
