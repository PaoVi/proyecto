# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, line-too-long
# pylint: disable=no-member, invalid-str-returned

from django.utils import timezone
from datetime import timedelta
# 🔹 STANDARD (PRIMERO)
from io import BytesIO
from decimal import Decimal
import uuid

# 🔹 THIRD PARTY
from django.conf import settings
import qrcode

# 🔹 DJANGO
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.files import File

# ==========================
#  Serie
# ==========================
class FacturaSerie(models.Model):
    establecimiento = models.CharField(max_length=3)
    punto_emision = models.CharField(max_length=3)
    timbrado = models.CharField(max_length=20, blank=True, default="")
    ultimo_numero = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("establecimiento", "punto_emision", "timbrado")

    def __str__(self):
        t = f" ({self.timbrado})" if self.timbrado else ""
        return f"{self.establecimiento}-{self.punto_emision}{t}"

    @classmethod
    def siguiente(cls, est, pto, timbrado=""):
        est = str(est).zfill(3)[:3]
        pto = str(pto).zfill(3)[:3]
        tim = (timbrado or "").strip()

        with transaction.atomic():
            serie, _ = cls.objects.select_for_update().get_or_create(
                establecimiento=est,
                punto_emision=pto,
                timbrado=tim,
            )
            serie.ultimo_numero += 1
            serie.save(update_fields=["ultimo_numero", "updated_at"])
            return serie.ultimo_numero


# ==========================
#  Factura
# ==========================
class Factura(models.Model):

    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", _("Activa")
        ANULADA = "ANULADA", _("Anulada")

    cliente_ruc = models.CharField(max_length=20, blank=True, default="")
    cliente_nombre = models.CharField(max_length=200, blank=True, default="")
    cliente_direccion = models.CharField(max_length=200, blank=True, default="")
    cliente_telefono = models.CharField(max_length=50, blank=True, default="")
    cliente = models.ForeignKey(
    'cliente.Cliente',
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name="facturas"
   )
    condicion_venta = models.CharField(
        max_length=10,
        choices=(("contado", "Contado"), ("credito", "Crédito")),
        default="contado"
    )

    establecimiento = models.CharField(max_length=3, default="001")
    punto_emision = models.CharField(max_length=3, default="001")
    timbrado = models.CharField(max_length=20, blank=True, default="")
    numero = models.IntegerField(default=0)

    fecha = models.DateField(default=timezone.localdate)

    iva = models.PositiveSmallIntegerField(
        choices=((10, "10%"), (5, "5%")),
        default=10
    )

    sin_ot = models.BooleanField(default=False)
    numero_ot = models.CharField(max_length=30, blank=True, default="")

    subtotal = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_iva = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_general = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA)
    entregada = models.BooleanField(default=False)

    configuracion_impresion = models.ForeignKey(
        'seguridad.ConfiguracionSistema',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='facturas'
    )

    observaciones = models.TextField(blank=True, default="")

    motivo_anulacion = models.TextField(
        _("Motivo de anulación"),
        blank=True,
        null=True,
        help_text=_("Motivo obligatorio al anular la factura")
    )
    usuario_anulacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Usuario que anuló")
    )
    fecha_nota_credito = models.DateTimeField(
        _("Fecha de Nota de Crédito"),
        null=True,
        blank=True,
        help_text=_("Fecha cuando se generó la Nota de Crédito")
    )

    class Meta:
        verbose_name = _("Factura")
        verbose_name_plural = _("Facturas")
        ordering = ("-fecha", "-id")
        permissions = [
            ("gestionar_facturas", "Puede gestionar facturas"),
            ("ver_facturas", "Puede ver facturas"),
            ("agregar_facturas", "Puede emitir facturas"),
            ("editar_facturas", "Puede actualizar facturas"),
            ("anular_facturas", "Puede anular facturas"),
            ("imprimir_facturas", "Puede imprimir facturas"),
            ("reimprimir_facturas", "Puede reimprimir facturas"),
            ("ver_reportes_facturas", "Puede ver reportes de facturas"),
        ] 

    # ELECTRÓNICA
    cdc = models.CharField(max_length=60, blank=True, null=True)
    qr = models.ImageField(upload_to='qr_facturas/', blank=True, null=True)
    fecha_generacion_electronica = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    @property
    def numero_formateado(self):
        return f"{self.establecimiento.zfill(3)}-{self.punto_emision.zfill(3)}-{int(self.numero):07d}"

    @property
    def tiene_nota_credito(self):
        return self.notas_credito.exists()  # Cualquier nota

    @property
    def nota_credito_activa(self):
        return self.notas_credito.order_by("-id").first()

    @property
    def nota_credito_antigua(self):
        """Verifica si la nota de crédito tiene más de 24 horas"""
        if not self.fecha_nota_credito:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() >= self.fecha_nota_credito + timedelta(hours=24)

    @property
    def debe_anularse(self):
        """Verifica si la factura debe anularse automáticamente"""
        return self.estado == self.Estado.ACTIVA and self.tiene_nota_credito and self.nota_credito_antigua
       
    def __str__(self):
        return str(self.numero_formateado)

    def clean(self):
        hoy = timezone.localdate()
        if self.fecha and self.fecha < hoy:
            raise ValidationError("Fecha inválida")

    def recalcular_totales(self, guardar=True):
        total = Decimal('0')

        for s in self.servicios.all():  # pylint: disable=no-member
            total += s.subtotal

        for i in self.insumos.all():  # pylint: disable=no-member
            total += i.subtotal

        if self.iva == 10:
            self.total_iva = total / Decimal('11')
        else:
            self.total_iva = total / Decimal('21')

        self.subtotal = total - self.total_iva
        self.total_general = total

        if guardar:
            super().save(update_fields=["subtotal", "total_iva", "total_general", "updated_at"])

    def generar_cdc(self):
        fecha_str = self.fecha.strftime('%Y%m%d') if self.fecha else ''
        base = f"{self.timbrado}{self.numero_formateado}{fecha_str}"
        return base + str(uuid.uuid4().int)[:10]

    def generar_qr(self):
        data = f"""
        CDC:{self.cdc}
        RUC:{self.cliente_ruc}
        TOTAL:{self.total_general}
        FECHA:{self.fecha}
        """

        qr_img = qrcode.make(data)

        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")

        file_name = f"qr_{self.numero_formateado}.png"

        return File(buffer, name=file_name)
    

    def anular(self, motivo="", usuario=None):
        """Anula la factura con motivo obligatorio"""
        if not motivo:
            raise ValidationError("El motivo de anulación es obligatorio")
        
        self.estado = self.Estado.ANULADA
        self.motivo_anulacion = motivo
        if usuario:
            self.usuario_anulacion = usuario
        if motivo:
            self.observaciones += f"\n[{timezone.now().strftime('%d/%m/%Y %H:%M')}] ANULADA: {motivo}"
        self.save(update_fields=["estado", "motivo_anulacion", "usuario_anulacion", "observaciones"])

    @classmethod
    def anular_facturas_vencidas(cls):
        """Anula automáticamente las facturas que tienen nota de crédito mayor a 24 horas"""
        
        limite = timezone.now() - timedelta(hours=24)
        
        facturas_a_anular = cls.objects.filter(
            estado=cls.Estado.ACTIVA,
            fecha_nota_credito__isnull=False,
            fecha_nota_credito__lte=limite
        )
        
        count = 0
        for factura in facturas_a_anular:
            factura.estado = cls.Estado.ANULADA
            factura.save(update_fields=['estado'])
            count += 1
        
        return count

    @property
    def puede_anular(self):
        """Verifica si la factura se puede anular (dentro de las 48 horas)"""
        if not self.fecha:
            return False
        
        # Combinar fecha con la hora de creación (o medianoche si no tiene)
        fecha_hora_emision = self.created_at if self.created_at else timezone.make_aware(
            timezone.datetime.combine(self.fecha, timezone.datetime.min.time())
        )
        
        limite = fecha_hora_emision + timedelta(hours=48)
        return timezone.now() <= limite

    def asignar_numero_si_corresponde(self):
        if not self.numero or self.numero <= 0:
            self.numero = FacturaSerie.siguiente(
                self.establecimiento,
                self.punto_emision,
                self.timbrado
            )

    def save(self, *args, **kwargs):

        if self.configuracion_impresion:
            config = self.configuracion_impresion  # evitar warning
            self.timbrado = getattr(config, "timbrado", "")
            self.establecimiento = getattr(config, "establecimiento", "001")
            self.punto_emision = getattr(config, "punto_expedicion", "001")

        self.establecimiento = str(self.establecimiento).zfill(3)[:3]
        self.punto_emision = str(self.punto_emision).zfill(3)[:3]

        self.asignar_numero_si_corresponde()

        super().save(*args, **kwargs)

        self.recalcular_totales()

        if not self.cdc:
            self.cdc = self.generar_cdc()
            self.generar_qr()
            self.fecha_generacion_electronica = timezone.now()
            super().save(update_fields=["cdc", "qr", "fecha_generacion_electronica"])

# ==========================
#  NOTA DE CRÉDITO
# ==========================
class NotaCredito(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    class Tipo(models.TextChoices):
        TOTAL = "TOTAL", "Total"
        PARCIAL = "PARCIAL", "Parcial"

    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name="notas_credito"
    )

    numero = models.IntegerField(default=0)
    establecimiento = models.CharField(max_length=3, default="001")
    punto_emision = models.CharField(max_length=3, default="001")
    timbrado = models.CharField(max_length=20, blank=True, default="")

    fecha = models.DateField(default=timezone.localdate)

    subtotal = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_iva = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_general = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    motivo = models.TextField(blank=True, default="")

    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        verbose_name="Estado de la Nota"
    )
    
    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.PARCIAL,
        help_text=_("Tipo de nota de crédito: TOTAL o PARCIAL")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    @property
    def numero_formateado(self):
        return f"{self.establecimiento.zfill(3)}-{self.punto_emision.zfill(3)}-{int(self.numero):07d}"

    @property
    def es_antigua(self):
        """Verifica si la nota de crédito tiene más de 24 horas"""
        if not self.created_at:
            return False
        
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        # Asegurar que ambas fechas tienen zona horaria
        if timezone.is_naive(self.created_at):
            from django.utils import timezone as tz
            created = timezone.make_aware(self.created_at)
        else:
            created = self.created_at
        
        # Calcular diferencia en horas
        diferencia = now - created
        return diferencia.total_seconds() >= 24 * 3600  # 24 horas en segundos

    def actualizar_estado_automatico(self):
        """Actualiza el estado de la nota de crédito a APROBADA si tiene más de 24 horas"""
        if self.estado == self.Estado.PENDIENTE and self.es_antigua:
            self.estado = self.Estado.APROBADA
            self.save(update_fields=['estado'])

            # ===== CREAR MOVIMIENTO FINANCIERO =====
            from finanza.views import crear_movimiento_nota_credito
            if self.total_general > 0:
                crear_movimiento_nota_credito(self)
                
            return True
        return False

    def __str__(self):
        return f"NC {self.numero_formateado}"

    def save(self, *args, **kwargs):

        if self.factura:
            self.timbrado = self.factura.timbrado
            self.establecimiento = self.factura.establecimiento
            self.punto_emision = self.factura.punto_emision

            # Los totales se cargan desde la vista según los ítems devueltos.
            # No copiar automáticamente los totales de la factura, porque la nota puede ser parcial.

        if not self.numero or self.numero <= 0:
            self.numero = FacturaSerie.siguiente(
                self.establecimiento,
                self.punto_emision,
                self.timbrado
            )

        super().save(*args, **kwargs)

# ==========================
# DETALLE DE NOTA DE CRÉDITO
# ==========================
class NotaCreditoDetalle(models.Model):
    nota = models.ForeignKey(NotaCredito, on_delete=models.CASCADE, related_name="detalles")
    descripcion = models.CharField(max_length=200)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return str(self.descripcion)


# ==========================
# DETALLES DE FACTURA
# ==========================
class FacturaServicio(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="servicios")
    descripcion = models.CharField(max_length=200)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return str(self.descripcion)


class FacturaInsumo(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="insumos")
    insumo = models.ForeignKey('insumo.Insumo', on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField(max_length=200)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return str(self.descripcion)
