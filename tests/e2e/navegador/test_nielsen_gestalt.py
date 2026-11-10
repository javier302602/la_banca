"""Correcciones de la evaluación heurística (Nielsen, severidad ≥ 3) y leyes de Gestalt medidas en el navegador.

Ver docs/investigacion/01_nielsen_gestalt.md.
"""
import re

from tests.e2e.navegador.conftest import iniciar_sesion, publicar, responder


def _caja(pagina, selector):
    return pagina.locator(selector).first.bounding_box()


def _estilo(pagina, selector, propiedad):
    return pagina.locator(selector).first.evaluate(f"n => getComputedStyle(n).{propiedad}")


def test_feed_similitud_proximidad_y_figura_fondo(navegador, servidor, usuarios):
    autor, lector = navegador.new_context(base_url=servidor), navegador.new_context(
        base_url=servidor, viewport={"width": 1366, "height": 900})
    try:
        iniciar_sesion(autor, "beto@unas.edu.pe")
        iniciar_sesion(lector, "ana@unas.edu.pe")
        for tipo in ("OFREZCO", "NECESITO", "ACTIVIDAD"):
            publicar(autor, f"Publicación {tipo.lower()}", tipo)
        iniciar_sesion(autor, "caro@unas.edu.pe")
        publicar(autor, "Otra oferta", "OFREZCO")
        p = lector.new_page()
        p.goto("/feed")
        p.locator(".tarjeta-publicacion").nth(3).wait_for()

        # Similitud: el mismo tipo comparte color y cada tipo tiene uno distinto
        colores = {t: {_estilo(p, f".tipo-{t} .etiqueta-tipo", "backgroundColor") for _ in range(1)}
                   for t in ("NECESITO", "OFREZCO", "ACTIVIDAD")}
        ofertas = p.locator(".tipo-OFREZCO .etiqueta-tipo")
        assert ofertas.count() == 2
        assert ofertas.nth(0).evaluate("n => getComputedStyle(n).backgroundColor") == \
            ofertas.nth(1).evaluate("n => getComputedStyle(n).backgroundColor")
        assert len({c.pop() for c in colores.values()}) == 3
        bordes = {t: _estilo(p, f".tarjeta-publicacion.tipo-{t}", "borderLeftColor") for t in ("NECESITO", "OFREZCO")}
        assert bordes["NECESITO"] != bordes["OFREZCO"]

        # Proximidad: dentro de la tarjeta, menos separación que entre tarjetas
        primera, segunda = p.locator(".tarjeta-publicacion").nth(0), p.locator(".tarjeta-publicacion").nth(1)
        etiquetas = primera.locator(".etiqueta-tipo").bounding_box()
        titulo = primera.locator("h2").bounding_box()
        interna = titulo["y"] - (etiquetas["y"] + etiquetas["height"])
        externa = segunda.bounding_box()["x"] - (primera.bounding_box()["x"] + primera.bounding_box()["width"])
        assert 0 <= interna < externa, (interna, externa)

        # Figura-fondo: las tarjetas (blancas) se separan del fondo de la página
        assert _estilo(p, "body", "backgroundColor") != _estilo(p, ".tarjeta-publicacion", "backgroundColor")
    finally:
        autor.close()
        lector.close()


def test_chat_agrupa_mensajes_consecutivos(navegador, servidor, usuarios):
    autor, lector = navegador.new_context(base_url=servidor), navegador.new_context(base_url=servidor)
    try:
        iniciar_sesion(autor, "beto@unas.edu.pe")
        iniciar_sesion(lector, "ana@unas.edu.pe")
        pid = autor.request.get("/api/publicaciones/mias").json()["items"][0]["id"]
        chat = responder(lector, pid, "Hola")
        for texto in ("Uno", "Dos"):
            autor.request.post(f"/api/chats/{chat}/mensajes", multipart={"texto": texto})
        lector.request.post(f"/api/chats/{chat}/mensajes", multipart={"texto": "Tres"})
        p = lector.new_page()
        p.goto(f"/chats/{chat}")
        p.locator("#historial .burbuja").nth(3).wait_for()
        cajas = [p.locator("#historial .burbuja").nth(i).bounding_box() for i in range(4)]
        separacion = [cajas[i + 1]["y"] - (cajas[i]["y"] + cajas[i]["height"]) for i in range(3)]
        # Hola(ana) → Uno(beto): cambio de autor · Uno → Dos: mismo autor · Dos → Tres: cambio de autor
        assert separacion[1] < separacion[0] and separacion[1] < separacion[2], separacion
        clases = [p.locator("#historial .burbuja").nth(i).get_attribute("class") for i in range(4)]
        assert "continua" in clases[2] and "continua" not in clases[1] and "continua" not in clases[3]
        # Figura-fondo: propias, ajenas y fondo del historial son distintos
        fondos = {_estilo(p, s, "backgroundColor") for s in (".burbuja.propia", ".burbuja.ajena", "#historial")}
        assert len(fondos) == 3
    finally:
        autor.close()
        lector.close()


def test_responder_muestra_la_publicacion(contexto, pagina, usuarios):
    """Nielsen H6 (severidad 3): quien responde ve a qué publicación responde."""
    iniciar_sesion(contexto, "beto@unas.edu.pe")
    pid = contexto.request.get("/api/publicaciones/mias").json()["items"][0]["id"]
    iniciar_sesion(contexto, "caro@unas.edu.pe")
    pagina.goto(f"/publicaciones/{pid}/responder")
    pagina.locator("#contexto:not(.d-none)").wait_for()
    assert pagina.inner_text("#contexto-autor") == "beto_9"
    assert pagina.inner_text("#contexto-titulo").startswith("Publicación")
    assert pagina.locator("#contexto-tipo.etiqueta-tipo").count() == 1


def test_cupo_lleno_se_avisa_antes_de_escribir(contexto, pagina, usuarios):
    """Nielsen H5 (severidad 3): sin cupo, el formulario avisa y no se puede enviar."""
    iniciar_sesion(contexto, "caro@unas.edu.pe")
    while contexto.request.get("/api/publicaciones/cupo").json()["activas"] < 3:
        publicar(contexto, "Relleno del cupo", "ACTIVIDAD")
    pagina.goto("/publicaciones/nueva")
    aviso = pagina.locator("#aviso-cupo:not(.d-none)")
    aviso.wait_for()
    assert "Ya tienes 3 publicaciones activas" in aviso.inner_text()
    assert aviso.locator("a[href='/publicaciones/mias']").count() == 1
    assert pagina.locator("#form-publicacion [type=submit]").is_disabled()


def test_menu_avisa_chats_con_mensajes_nuevos(navegador, servidor, usuarios):
    """Nielsen H1 (severidad 3): el menú muestra cuántos chats tienen mensajes sin leer."""
    autor, lector = navegador.new_context(base_url=servidor), navegador.new_context(base_url=servidor)
    try:
        iniciar_sesion(autor, "beto@unas.edu.pe")
        iniciar_sesion(lector, "caro@unas.edu.pe")
        pid = autor.request.get("/api/publicaciones/mias").json()["items"][0]["id"]
        chat = responder(lector, pid, "¿Sigue disponible?")
        p = autor.new_page()
        p.goto("/feed")
        insignia = p.locator("#nav-no-leidos:not(.d-none)")
        insignia.wait_for()
        assert re.fullmatch(r"\d+ nuevos?", insignia.inner_text())
        antes = int(insignia.inner_text().split()[0])
        p.goto(f"/chats/{chat}")  # al abrirlo se marca como leído
        p.locator("#historial .burbuja").first.wait_for()
        p.goto("/feed")
        p.locator(".tarjeta-publicacion").first.wait_for()
        p.wait_for_function("() => document.querySelector('#nav-no-leidos').dataset.cargado === '1'")
        texto = p.inner_text("#nav-no-leidos") if p.locator("#nav-no-leidos").is_visible() else ""
        assert (int(texto.split()[0]) if texto else 0) == antes - 1
    finally:
        autor.close()
        lector.close()
