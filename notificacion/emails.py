from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone
from seguridad.utils import obtener_configuracion
from .models import LogEnvio


# --- Helpers para leer config ---
def cfg_bool(clave: str, default: bool = False) -> bool:
    val = obtener_configuracion(clave, default)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes", "si", "verdadero")

def cfg_str(clave: str, default: str = "") -> str:
    val = obtener_configuracion(clave, default)
    return "" if val is None else str(val)

def cfg_int(clave: str, default: int) -> int:
    try:
        return int(obtener_configuracion(clave, default))
    except Exception:
        return default


# --- From visible ---
def _from_email() -> str:
    """
    Remitente visual. Para Gmail, debe ser igual al smtp_user o un alias verificado.
    """
    remitente_cfg = cfg_str("email_notificaciones", "")
    return remitente_cfg or getattr(settings, "DEFAULT_FROM_EMAIL", "")


# --- Conexión SMTP dinámica ---
def _smtp_connection():
    host = cfg_str("smtp_host", getattr(settings, "EMAIL_HOST", "smtp.gmail.com"))
    port = cfg_int("smtp_port", getattr(settings, "EMAIL_PORT", 587))
    use_tls = cfg_bool("smtp_use_tls", getattr(settings, "EMAIL_USE_TLS", True))
    use_ssl = cfg_bool("smtp_use_ssl", getattr(settings, "EMAIL_USE_SSL", False))
    username = cfg_str("smtp_user", getattr(settings, "EMAIL_HOST_USER", ""))
    password = cfg_str("smtp_password", getattr(settings, "EMAIL_HOST_PASSWORD", ""))

    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=host,
        port=port,
        username=username,
        password=password,
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout=getattr(settings, "EMAIL_TIMEOUT", None),
    )


def enviar_bienvenida(destinatario: str, nombre: str, cliente_id: int, *, force: bool = False) -> bool:
    """
    Envía correo de bienvenida (SOLO HTML).
    Lee TODO desde Configuración del Sistema.
    No envía si notificaciones_habilitadas está en false o inactiva.
    Evita duplicados exitosos salvo force=True.
    """
    # 1) Habilitado?
    if not cfg_bool("notificaciones_habilitadas", False):
        LogEnvio.objects.create(
            tipo="bienvenida",
            referencia_id=cliente_id,
            email=destinatario,
            asunto="(SKIP) Bienvenida deshabilitada",
            exito=False,
            detalle="notificaciones_habilitadas = False o inactiva",
            creado_en=timezone.now(),
        )
        return False

    # 2) Evitar duplicados
    if not force and LogEnvio.objects.filter(
        tipo="bienvenida", referencia_id=cliente_id, exito=True
    ).exists():
        LogEnvio.objects.create(
            tipo="bienvenida",
            referencia_id=cliente_id,
            email=destinatario,
            asunto="(SKIP) Bienvenida ya enviada",
            exito=False,
            detalle="Previamente enviada con éxito",
            creado_en=timezone.now(),
        )
        return False

    # 3) Contenido
    subject = "¡Bienvenido/a al Taller Iam Car!"
    context = {"nombre": nombre}
    html_body = render_to_string("notificacion/email_bienvenida.html", context)

    # 4) Remitente/BCC
    from_email = _from_email()
    bcc_email = cfg_str("email_notificaciones_bcc", "")
    bcc_list = [bcc_email] if bcc_email else None

    # 5) SMTP creds
    connection = _smtp_connection()
    smtp_user = cfg_str("smtp_user", "")
    if not smtp_user:
        LogEnvio.objects.create(
            tipo="bienvenida",
            referencia_id=cliente_id,
            email=destinatario,
            asunto="(SKIP) Falta smtp_user",
            exito=False,
            detalle="Config smtp_user vacía",
            creado_en=timezone.now(),
        )
        return False

    # 6) Coherencia Gmail (opcional: loguear si puede fallar)
    if from_email and smtp_user and from_email.lower() != smtp_user.lower():
        # Si usás Gmail, from_email debe ser alias verificado en smtp_user
        # No bloqueamos, pero lo dejamos registrado para diagnóstico.
        alias_note = f"From '{from_email}' distinto a smtp_user '{smtp_user}'. Requiere alias verificado en Gmail."
    else:
        alias_note = "From coincide con smtp_user."

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=html_body,          # SOLO HTML
            from_email=from_email or smtp_user,
            to=[destinatario],
            bcc=bcc_list,
            reply_to=[from_email or smtp_user],
            connection=connection,
        )
        msg.content_subtype = "html"
        msg.send()

        LogEnvio.objects.create(
            tipo="bienvenida",
            referencia_id=cliente_id,
            email=destinatario,
            asunto=subject,
            exito=True,
            detalle=f"Enviado desde {from_email or smtp_user}. {alias_note}",
            creado_en=timezone.now(),
        )
        return True

    except Exception as e:
        LogEnvio.objects.create(
            tipo="bienvenida",
            referencia_id=cliente_id,
            email=destinatario,
            asunto=subject,
            exito=False,
            detalle=str(e),
            creado_en=timezone.now(),
        )
        return False
