"""RNF-USA-03 (error junto al campo), RNF-USA-06 (conservar datos salvo contraseñas) y RNF-USA-07 (etiquetas)."""
from tests.e2e.navegador.conftest import CLAVE, iniciar_sesion, publicar, responder


def _error_del_campo(pagina, campo: str) -> str:
    """Texto del error asociado al campo por aria-describedby, comprobando la asociación accesible."""
    aviso = pagina.locator(f"#error-{campo}")
    aviso.wait_for()
    control = pagina.locator(f"[name='{campo}']").first
    assert control.get_attribute("aria-invalid") == "true"
    assert f"error-{campo}" in (control.get_attribute("aria-describedby") or "").split()
    return aviso.inner_text()


def _llenar_registro(pagina, correo, nickname="nuevo_1", clave=CLAVE, confirmacion=CLAVE):
    pagina.goto("/registro")
    pagina.fill("#correo", correo)
    pagina.fill("#nickname", nickname)
    pagina.fill("#contrasena", clave)
    pagina.fill("#confirmacion", confirmacion)
    pagina.check("#acepta_terminos")
    pagina.click("button[type=submit]")


def test_registro_error_de_dominio_junto_al_correo_y_vacia_contrasenas(pagina, usuarios):
    _llenar_registro(pagina, "alguien@gmail.com")
    assert _error_del_campo(pagina, "correo") == "Debes usar tu correo institucional (@unas.edu.pe)"
    assert pagina.evaluate("document.activeElement.id") == "correo"  # el foco va al campo con error
    # RNF-USA-06: los demás datos se conservan; las contraseñas se vacían
    assert pagina.input_value("#correo") == "alguien@gmail.com" and pagina.input_value("#nickname") == "nuevo_1"
    assert pagina.is_checked("#acepta_terminos")
    assert pagina.input_value("#contrasena") == "" and pagina.input_value("#confirmacion") == ""
    assert pagina.locator("#mensajes .alert").count() == 0  # sin aviso general duplicado


def test_registro_confirmacion_y_nickname_ocupado_en_su_campo(pagina, usuarios):
    _llenar_registro(pagina, "otra@unas.edu.pe", confirmacion="distinta1")
    assert _error_del_campo(pagina, "confirmacion") == "Las contraseñas no coinciden"
    assert pagina.locator("#error-correo").count() == 0

    pagina.fill("#nickname", "ANA_07")  # ocupado sin distinguir mayúsculas (error de dominio con su campo)
    pagina.fill("#contrasena", CLAVE)
    pagina.fill("#confirmacion", CLAVE)
    pagina.click("button[type=submit]")
    assert _error_del_campo(pagina, "nickname") == "Ese nickname ya está en uso. Elige otro"
    assert pagina.locator("#error-confirmacion").count() == 0  # el error anterior se retira
    assert pagina.input_value("#contrasena") == ""


def test_login_fallido_vacia_la_contrasena_y_conserva_el_correo(pagina, usuarios):
    pagina.goto("/login")
    pagina.fill("#correo", "ana@unas.edu.pe")
    pagina.fill("#contrasena", "incorrecta1")
    pagina.click("button[type=submit]")
    pagina.locator("#mensajes .alert").wait_for()  # sin campo propio: no revela cuál dato falló (RF-AUT-09)
    assert "Correo o contraseña incorrectos" in pagina.inner_text("#mensajes")
    assert pagina.input_value("#correo") == "ana@unas.edu.pe" and pagina.input_value("#contrasena") == ""


def test_crear_publicacion_errores_en_tipo_y_titulo(contexto, pagina, usuarios):
    iniciar_sesion(contexto, "caro@unas.edu.pe")
    pagina.goto("/publicaciones/nueva")
    pagina.fill("#titulo", "   ")
    pagina.fill("#descripcion", "Detalle")
    pagina.click("button[type=submit]")
    assert _error_del_campo(pagina, "tipo") == "Selecciona el tipo de publicación"
    assert pagina.locator("fieldset #error-tipo").count() == 1  # dentro del grupo de opciones

    pagina.check("#tipo-NECESITO")
    pagina.click("button[type=submit]")
    assert _error_del_campo(pagina, "titulo") == "Debes ingresar el título"
    assert pagina.locator("#error-tipo").count() == 0 and pagina.input_value("#descripcion") == "Detalle"


def test_chat_error_junto_al_mensaje_y_etiquetas_visibles(navegador, servidor, usuarios):
    autor = navegador.new_context(base_url=servidor)
    lector = navegador.new_context(base_url=servidor)
    try:
        iniciar_sesion(autor, "beto@unas.edu.pe")
        iniciar_sesion(lector, "ana@unas.edu.pe")
        chat_id = responder(lector, publicar(autor, "Calculadora prestada"))
        pagina = lector.new_page()
        pagina.goto(f"/chats/{chat_id}")
        pagina.locator("#chat:not(.d-none)").wait_for()
        # RNF-USA-07: etiquetas visibles del mensaje y de la imagen
        assert pagina.locator("label[for=texto]").is_visible() and pagina.locator("label[for=imagen]").is_visible()
        pagina.click("#form-mensaje button[type=submit]")
        assert _error_del_campo(pagina, "texto") == "Escribe un mensaje, adjunta una imagen o un documento, o elige un sticker"
    finally:
        autor.close()
        lector.close()


def test_filtro_del_feed_tiene_etiqueta_visible(contexto, pagina, usuarios):
    iniciar_sesion(contexto, "caro@unas.edu.pe")
    pagina.goto("/feed")
    etiqueta = pagina.locator("label[for=filtro-tipo]")
    assert etiqueta.is_visible() and etiqueta.inner_text() == "Tipo"
