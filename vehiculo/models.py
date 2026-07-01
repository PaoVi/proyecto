from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date
import re
from cliente.models import Cliente

# VALIDADORES

# Chapa: flexible (alfa-num/guion/punto) 4–12.
# El form sugiere PY (ABC123 / ABC1234), pero acá admitimos variantes especiales.
patente_validator = RegexValidator(
    regex=r"^[A-Z0-9\-\.]{4,12}$",
    message=_("Formato de chapa inválido (use 4–12 caracteres alfanuméricos; se permiten guion y punto)."),
)

# Chasis: VIN moderno (17 sin I/O/Q) o legacy (9–14 sin I/O/Q).
CHASIS_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{9,17}$")
def chasis_validator(value: str):
    v = (value or "").strip().upper()
    if not CHASIS_RE.match(v):
        raise ValidationError(_("Número de chasis inválido. Use VIN de 17 (sin I, O, Q) o chasis antiguo 9–14 caracteres."))

def validate_max_year(value: int):
    limit = date.today().year + 1
    if value > limit:
        raise ValidationError(_("El año no puede ser mayor a %(limit)s."), params={"limit": limit})


class Vehiculo(models.Model):
    class Combustible(models.TextChoices):
        NAFTA = "Nafta", _("Nafta/Gasolina")
        DIESEL = "Diésel", _("Diésel")
        ELECTRICO = "Eléctrico", _("Eléctrico")
        HIBRIDO = "Híbrido", _("Híbrido")
        GNC = "GNC", _("GNC")

    class Uso(models.TextChoices):
        PARTICULAR = "Particular", _("Particular")
        COMERCIAL = "Comercial", _("Comercial")
        OFICIAL = "Oficial", _("Oficial")
        PARTICULAR_COMERCIAL = "Particular/Comercial", _("Particular/Comercial")

    class ViaImportacion(models.TextChoices):
        LOCAL = "LOCAL", _("Compra local")
        IMPORTADO = "IMPORTADO", _("Importado")
        REMATE = "REMATE", _("Remate")
        DIPLOMATICO = "DIPLOMATICO", _("Diplomático")

    class Procedencia(models.TextChoices):
        PY = "PY", _("Paraguay")
        BR = "BR", _("Brasil")
        AR = "AR", _("Argentina")
        US = "US", _("Estados Unidos")
        JP = "JP", _("Japón")
        KR = "KR", _("Corea")
        EU = "EU", _("Europa")
        OTRO = "OTRO", _("Otro")

    class Transmision(models.TextChoices):
        MANUAL = "MANUAL", _("Manual")
        AUTOMATICA = "AUTOMATICA", _("Automática")
        CVT = "CVT", _("CVT")
        SECUENCIAL = "SECUENCIAL", _("Secuencial/DCT")

    id_vehiculo = models.AutoField(primary_key=True)

    propietario = models.ForeignKey(
        'cliente.Cliente', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Propietario")
    )
    
    poseedor = models.ForeignKey(
        'cliente.Cliente', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Poseedor/Responsable"),
        related_name='vehiculos_poseedor' 
    )
    

    marca = models.CharField(_("Marca"), max_length=80)
    modelo = models.CharField(_("Modelo"), max_length=120)
    anio = models.PositiveIntegerField(
        _("Año"),
        validators=[MinValueValidator(1900, message=_("El año no puede ser menor a 1900.")), validate_max_year]
    )
    color = models.CharField(_("Color"), max_length=50)

    nro_chapa = models.CharField(
        _("Nro. de chapa"),
        max_length=20,
        unique=True,
        validators=[patente_validator],
        help_text=_("Sugerido PY: ABC123 o ABC1234; también se aceptan otros formatos alfanuméricos."),
        error_messages={"unique": _("Ya existe un vehículo con esta chapa.")},
        null=True,
        blank=True
    )
    nro_chasis = models.CharField(
        _("Nro. de chasis"),
        max_length=20,
        unique=True,
        validators=[chasis_validator],
        help_text=_("VIN de 17 (sin I/O/Q) o chasis antiguo 9–14."),
        error_messages={"unique": _("Ya existe un vehículo con este número de chasis.")},
    )

    cantidad_puerta = models.PositiveSmallIntegerField(
        _("Cantidad de puertas"),
        null=True, blank=True,
        validators=[MinValueValidator(1, message=_("Debe ser al menos 1."))],
    )
    motor_cilindrada = models.CharField(
        _("Cilindrada del motor"), max_length=20, null=True, blank=True
    )

    tipo_combustible = models.CharField(
        _("Tipo de combustible"),
        max_length=15,
        choices=Combustible.choices
    )
    uso = models.CharField(
        _("Uso"),
        max_length=25,
        choices=Uso.choices
    )
    cedula_verde = models.BooleanField(_("Cédula verde"), default=False)
    via_importacion = models.CharField(
        _("Vía de importación"),
        max_length=15,
        choices=ViaImportacion.choices
    )
    procedencia = models.CharField(
        _("Procedencia"),
        max_length=10,
        choices=Procedencia.choices
    )
    tipo_transmision = models.CharField(
        _("Tipo de transmisión"),
        max_length=15,
        choices=Transmision.choices
    )

    alarma = models.BooleanField(_("Alarma"), default=False)
    gps = models.BooleanField(_("GPS"), default=False)

    fecha_registro = models.DateTimeField(_("Fecha de registro"), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_("Fecha de actualización"), auto_now=True)
    estado = models.BooleanField(_("Activo"), default=True)

    class Meta:
        verbose_name = _("Vehículo")
        verbose_name_plural = _("Vehículos")
        ordering = ("-fecha_registro",)
        permissions = [
            ("gestionar_vehiculos", "Puede gestionar vehículos"),
            ("ver_vehiculos", "Puede ver vehículos"),
            ("agregar_vehiculos", "Puede registrar vehículos"),
            ("editar_vehiculos", "Puede actualizar vehículos"),
        ]

    def __str__(self):
        return f"{self.marca} {self.modelo} {self.anio} [{self.nro_chapa}]"

    def clean(self):
        super().clean()

        # Normalizaciones para evitar duplicados por espacios/minúsculas
        if self.nro_chapa:
            self.nro_chapa = re.sub(r"\s+", "", self.nro_chapa.upper())
        if self.nro_chasis:
            self.nro_chasis = re.sub(r"\s+", "", self.nro_chasis.upper())

        # Refuerzos (por si cambian validadores)
        if self.anio and self.anio < 1900:
            raise ValidationError({"anio": _("El año no puede ser menor a 1900.")})
        limit = date.today().year + 1
        if self.anio and self.anio > limit:
            raise ValidationError({"anio": _("El año no puede ser mayor a %(limit)s.") % {"limit": limit}})