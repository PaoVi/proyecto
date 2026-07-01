from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
from datetime import date
import calendar


# VALIDADORES 
cedula_validator = RegexValidator(
    regex=r'^[0-9]{5,8}$',
    message=_("Formato inválido para cédula. Ej.: 1234567"),
)

ruc_validator = RegexValidator(
    regex=r'^[0-9]{5,12}-[0-9]{1}$',
    message=_("Formato inválido para RUC. Ej.: 80012345-1"),
)

pasaporte_validator = RegexValidator(
    regex=r'^[A-Z0-9]{6,12}$',
    message=_("Formato inválido para pasaporte. Ej.: AB123456"),
)

otro_documento_validator = RegexValidator(
    regex=r'^[A-Za-z0-9\s\-]{3,20}$',
    message=_("Formato inválido para otro documento."),
)

telefono_py_validator = RegexValidator(
    regex=r'^\+?595[0-9]{7,9}$',
    message=_("Formato recomendado: +595xxxxxxx"),
)

# CLIENTES
class Cliente(models.Model):
    class TipoCliente(models.TextChoices):
        fisica = "fisica", _("Persona Física")
        juridica = "juridica", _("Persona Jurídica")

    TIPO_DOC = [
        ("CI_PY", _("Cédula Paraguaya")),
        ("RUC", _("Registro Único de Contribuyente")),
        ("PAS", _("Pasaporte")),
        ("OTRO", _("Otro documento")),
    ]

    tipo_cliente = models.CharField(
        max_length=10,
        choices=TipoCliente.choices,
        default=TipoCliente.fisica,
        verbose_name=_("Tipo de cliente"),
    )

    tipo_documento = models.CharField(max_length=10, choices=TIPO_DOC, verbose_name=_("Tipo Documento"))
    numero_documento = models.CharField(max_length=20, unique=True) 
    nombre = models.CharField(max_length=150, verbose_name=_("Nombre completo"))
    telefono = models.CharField(
        max_length=20,
        validators=[telefono_py_validator],
        verbose_name=_("Teléfono"),
        help_text=_("Formato recomendado: +5959xxxxxxx"),
        error_messages={
            "required": _("Debe ingresar un número de teléfono."),
            "blank": _("Debe ingresar un número de teléfono."),
        },
    )
    email = models.EmailField(blank=True, null=True, validators=[EmailValidator(message=_("Correo inválido"))])
    direccion = models.TextField(blank=True, null=True)

    fecha_nacimiento = models.DateField(
        null=True, blank=True,
        verbose_name=_("Fecha de nacimiento"),
    )
    fecha_constitucion = models.DateField(
        null=True, blank=True,
        verbose_name=_("Fecha de constitución"),
    )

    is_active = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")
        ordering = ("-fecha_registro",)
        permissions = [
            ("gestionar_clientes", "Puede gestionar clientes"),
            ("ver_clientes", "Puede ver clientes"),
            ("agregar_clientes", "Puede registrar clientes"),
            ("editar_clientes", "Puede actualizar clientes"),
            ("desactivar_clientes", "Puede desactivar clientes"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.numero_documento})"

    def clean(self):
        super().clean()
        hoy = date.today() 

        # Validar formato del número de documento según tipo
        if self.tipo_documento == "CI_PY":
            if not cedula_validator.regex.match(self.numero_documento):
                raise ValidationError({"numero_documento": cedula_validator.message})
        elif self.tipo_documento == "RUC":
            if not ruc_validator.regex.match(self.numero_documento):
                raise ValidationError({"numero_documento": ruc_validator.message})
        elif self.tipo_documento == "PAS":
            if not pasaporte_validator.regex.match(self.numero_documento):
                raise ValidationError({"numero_documento": pasaporte_validator.message})
        elif self.tipo_documento == "OTRO":
            if not otro_documento_validator.regex.match(self.numero_documento):
                raise ValidationError({"numero_documento": otro_documento_validator.message})

        def validar_dia_por_mes(fecha, field_name):
            if not fecha:
                return
            max_dia_mes = calendar.monthrange(fecha.year, fecha.month)[1]

            if fecha.month == 2 and fecha.day == 29 and not calendar.isleap(fecha.year):
                raise ValidationError({
                    field_name: _("El {0} no es bisiesto; no se permite el 29 de febrero.").format(fecha.year)
                })

            if fecha.day > max_dia_mes:
                if fecha.month == 2:
                    raise ValidationError({
                        field_name: _("Febrero de {0} sólo tiene {1} días.").format(fecha.year, max_dia_mes)
                    })
                elif max_dia_mes == 30:
                    raise ValidationError({
                        field_name: _("El mes ingresado solo tiene 30 días.")
                    })
                else:
                    raise ValidationError({
                        field_name: _("El mes ingresado solo tiene 31 días.")
                    })

        if self.tipo_cliente == self.TipoCliente.fisica:
            if self.fecha_nacimiento:
                if self.fecha_nacimiento > hoy:
                    raise ValidationError({"fecha_nacimiento": _("La fecha de nacimiento no puede ser mayor a la fecha actual.")})
                if self.fecha_nacimiento.year < 1900:
                    raise ValidationError({"fecha_nacimiento": _("La fecha de nacimiento es demasiado antigua.")})
                validar_dia_por_mes(self.fecha_nacimiento, "fecha_nacimiento")

                edad = hoy.year - self.fecha_nacimiento.year - (
                    (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
                )
                if edad < 18:
                    raise ValidationError({"fecha_nacimiento": _("El cliente debe ser mayor de 18 años.")})

        elif self.tipo_cliente == self.TipoCliente.juridica:
            if self.fecha_constitucion:
                if self.fecha_constitucion > hoy:
                    raise ValidationError({"fecha_constitucion": _("La fecha de constitución no puede ser mayor a la fecha actual.")})
                if self.fecha_constitucion.year < 1800:
                    raise ValidationError({"fecha_constitucion": _("La fecha de constitución es demasiado antigua.")})
                validar_dia_por_mes(self.fecha_constitucion, "fecha_constitucion")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class NotificacionCliente(models.Model):
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name="notificaciones")
    email_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Preferencia de Notificación")
        verbose_name_plural = _("Preferencias de Notificación")

    def __str__(self):
        return f"Notificaciones de {self.cliente.nombre}"
