# pylint: disable=no-member
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F
from django.utils import timezone


# ==========================================================
# CAJA
# ==========================================================

class Caja(models.Model):

    ESTADO_CHOICES = [

        ("abierta", "Abierta"),

        ("cerrada", "Cerrada"),
    ]

    fecha_apertura = models.DateTimeField(
        default=timezone.now
    )

    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True
    )

    monto_inicial = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    saldo_actual = models.DecimalField(
    max_digits=15,
    decimal_places=2,
    default=0,
    validators=[MinValueValidator(0)]
    )

    total_ingresos_cierre = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    total_egresos_cierre = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    saldo_cierre = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="abierta"
    )

    usuario_apertura = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cajas_abiertas"
    )

    usuario_cierre = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cajas_cerradas",
        null=True,
        blank=True
    )

    observacion = models.TextField(
        blank=True,
        null=True
    )

    class Meta:

        verbose_name = "Caja"

        verbose_name_plural = "Cajas"

        ordering = ["-fecha_apertura"]

        permissions = [

            ("ver_finanzas", "Puede ver finanzas"),
            ("gestionar_finanzas", "Puede gestionar finanzas"),
            ("abrir_caja", "Puede abrir caja"),
            ("cerrar_caja", "Puede cerrar caja"),
            ("ver_reportes_financieros","Puede ver reportes financieros"),
        ] 

    def __str__(self):

        return f"Caja #{self.id}"

    @property
    def total_ingresos(self):

        return self.movimientos.filter(
            tipo="ingreso"
        ).aggregate(
            total=models.Sum("monto")
        )["total"] or Decimal("0.00")
    @property
    def total_egresos(self):

        return self.movimientos.filter(
            tipo="egreso"
        ).aggregate(
            total=models.Sum("monto")
        )["total"] or Decimal("0.00")

# ==========================================================
# MOVIMIENTO FINANCIERO
# ==========================================================

class MovimientoFinanciero(models.Model):

    TIPO_CHOICES = [

        ("ingreso", "Ingreso"),

        ("egreso", "Egreso"),
    ]

    ORIGEN_CHOICES = [

        ("factura", "Factura"),

        ("compra", "Compra"),

        ("manual", "Manual"),
    ]

    caja = models.ForeignKey(
        Caja,
        on_delete=models.CASCADE,
        related_name="movimientos"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES
    )

    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default="manual"
    )

    descripcion = models.CharField(
        max_length=255
    )

    monto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    fecha = models.DateTimeField(
        default=timezone.now
    )

    factura = models.ForeignKey(
        "factura.Factura",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    compra = models.ForeignKey(
        "compra.Compra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:

        verbose_name = "Movimiento Financiero"

        verbose_name_plural = (
            "Movimientos Financieros"
        )

        ordering = ["-fecha"]

    def __str__(self):

        return (
            f"{self.tipo.upper()} - "
            f"{self.monto}"
        )

    def actualizar_saldo_caja(self):

        caja = self.caja

        ingresos = caja.total_ingresos

        egresos = caja.total_egresos

        caja.saldo_actual = (
            caja.monto_inicial
            + ingresos
            - egresos
        )
        caja.save(
            update_fields=["saldo_actual"]
        )
    def save(self, *args, **kwargs):

        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new:
            self.actualizar_saldo_caja()


# ==========================================================
# CUENTAS POR COBRAR
# ==========================================================

class CuentaCobrar(models.Model):

    factura = models.OneToOneField(
        "factura.Factura",
        on_delete=models.CASCADE,
        related_name="cuenta_cobrar"
    )

    cliente = models.ForeignKey(
        "cliente.Cliente",
        on_delete=models.CASCADE
    )

    monto_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    monto_pagado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    saldo_pendiente = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    fecha_vencimiento = models.DateField()

    pagado = models.BooleanField(
        default=False
    )

    class Meta:

        verbose_name = (
            "Cuenta por Cobrar"
        )
        verbose_name_plural = (
            "Cuentas por Cobrar"
        )
    def save(self, *args, **kwargs):

        self.saldo_pendiente = (
            self.monto_total - self.monto_pagado
        )

        self.pagado = (
            self.saldo_pendiente <= 0
        )

        super().save(*args, **kwargs)
    def __str__(self):

        return (
            f"Cuenta Cobrar "
            f"#{self.factura_id}"
        )
# ==========================================================
# CUENTAS POR PAGAR
# ==========================================================
class CuentaPagar(models.Model):

    compra = models.OneToOneField(
        "compra.Compra",
        on_delete=models.CASCADE,
        related_name="cuenta_pagar"
    )

    proveedor = models.ForeignKey(
        "proveedor.Proveedor",
        on_delete=models.CASCADE
    )

    monto_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    monto_pagado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    saldo_pendiente = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    fecha_vencimiento = models.DateField()
    pagado = models.BooleanField(
        default=False )

    class Meta:

        verbose_name = "Cuenta por Pagar"
        verbose_name_plural = "Cuentas por Pagar"
    def save(self, *args, **kwargs):
        self.saldo_pendiente = (
            self.monto_total - self.monto_pagado
        )

        self.pagado = (
            self.saldo_pendiente <= 0
        )

        super().save(*args, **kwargs)
    def __str__(self):

        return f"Cuenta Pagar #{self.compra_id}"
# ==========================================================
# COBRO
# ==========================================================

class Cobro(models.Model):

    cuenta = models.ForeignKey(
        CuentaCobrar,
        on_delete=models.CASCADE,
        related_name="cobros"
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    monto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    observacion = models.TextField(
        blank=True,
        null=True
    )

    class Meta:

        verbose_name = "Cobro"

        verbose_name_plural = "Cobros"

        ordering = ["-fecha"]

    def save(self, *args, **kwargs):

        nuevo = self.pk is None

        super().save(*args, **kwargs)

        if nuevo:

            CuentaCobrar.objects.filter(
                pk=self.cuenta_id
            ).update(
                monto_pagado=F("monto_pagado") + self.monto
            )
            self.cuenta.refresh_from_db()
            self.cuenta.save()

    def __str__(self):

        return f"Cobro #{self.id}"
# ==========================================================
# PAGO PROVEEDOR
# ==========================================================

class PagoProveedor(models.Model):

    cuenta = models.ForeignKey(
        CuentaPagar,
        on_delete=models.CASCADE,
        related_name="pagos"
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    monto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    observacion = models.TextField(
        blank=True,
        null=True
    )

    class Meta:

        verbose_name = "Pago Proveedor"

        verbose_name_plural = "Pagos Proveedores"

        ordering = ["-fecha"]

    def save(self, *args, **kwargs):

        nuevo = self.pk is None

        super().save(*args, **kwargs)

        if nuevo:

            CuentaPagar.objects.filter(
                pk=self.cuenta_id
            ).update(
                monto_pagado=F("monto_pagado") + self.monto
            )
            self.cuenta.refresh_from_db()
            self.cuenta.save()

    def __str__(self):

        return f"Pago #{self.id}"
