from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
import re

# VALIDADORES
ruc_validator = RegexValidator(
    regex=r'^[0-9]{5,12}(-[0-9]{1})?$',
    message=_("Formato inválido. Ej. 80012345-1"),
)

telefono_py_validator = RegexValidator(
    regex=r'^\+?595[0-9]{7,9}$',
    message=_("Formato recomendado: +5959xxxxxxx"),
)

# PROVEEDORES
class Proveedor(models.Model):
    ruc = models.CharField(
        max_length=20,
        unique=True,
        validators=[ruc_validator],
        verbose_name=_("RUC"),
        error_messages={
            "unique": _("Ya existe un proveedor con este RUC."),
        },
    )

    razon_social = models.CharField(_("Razón social"), max_length=150)
    nombre_fantasia = models.TextField(blank=True, null=True)

    telefono = models.CharField(
        max_length=20,
        validators=[telefono_py_validator],
        verbose_name=_("Teléfono"),
        help_text=_("Formato recomendado: +5959xxxxxxx"),
    )
    email = models.EmailField(
        blank=True, null=True, validators=[EmailValidator(message=_("Correo inválido"))]
    )
    ciudad = models.TextField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    contacto_nombre = models.CharField(
        _("Persona de contacto"), max_length=120, blank=True, null=True
    )
    contacto_telefono = models.CharField(
        _("Teléfono de contacto"),
        max_length=20,
        blank=True,
        null=True,
        validators=[telefono_py_validator],
        help_text=_("Formato recomendado: +5959xxxxxxx"),
    )

    is_active = models.BooleanField(_("Activo"), default=True)
    fecha_registro = models.DateTimeField(_("Fecha de registro"), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_("Fecha de actualización"), auto_now=True)

    class Meta:
        verbose_name = _("Proveedor")
        verbose_name_plural = _("Proveedores")
        ordering = ("-fecha_registro",)
        permissions = [
            ("gestionar_proveedores", "Puede gestionar proveedores"),
            ("ver_proveedores", "Puede ver proveedores"),
            ("agregar_proveedores", "Puede registrar proveedores"),
            ("editar_proveedores", "Puede actualizar proveedores"),
            ("desactivar_proveedores", "Puede desactivar/activar proveedores"),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.ruc})"

    def clean(self):
        super().clean()

        # Normalización básica (quitar espacios)
        if self.ruc:
            self.ruc = re.sub(r"\s+", "", self.ruc)

        # Requerir guion en el RUC (p.ej. 8001234-6)
        # Si prefieres solo recomendarlo, comenta el raise de abajo.
        if self.ruc and "-" not in self.ruc:
            raise ValidationError({
                "ruc": _("El RUC debe incluir guión. Ej. 80012345-1")
            })
    
        if self.razon_social:
            self.razon_social = self.razon_social.strip().upper()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class NotificacionProveedor(models.Model):
    proveedor = models.OneToOneField(
        Proveedor, on_delete=models.CASCADE, related_name="notificaciones"
    )
    email_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Preferencia de Notificación de Proveedor")
        verbose_name_plural = _("Preferencias de Notificación de Proveedor")

    def __str__(self):
        return f"Notificaciones de {self.proveedor.razon_social}"
