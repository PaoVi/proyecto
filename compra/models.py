# pylint: disable=E1101,no-member,broad-exception-caught
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta, date
import calendar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ==========================================================
# FECHA ENTREGA DEFAULT
# ==========================================================

def default_fecha_entrega_esperada():

    return (
        timezone.now() + timedelta(days=15)
    ).date()


# ==========================================================
# DETALLE PRODUCTOS COMPRA
# ==========================================================

class CompraProducto(models.Model):

    compra = models.ForeignKey(

        "Compra",

        on_delete=models.CASCADE,

        verbose_name=_("Orden de Compra"),

        related_name="detalles",
    )

    producto = models.ForeignKey(

        "insumo.Insumo",

        on_delete=models.CASCADE,

        verbose_name=_("Producto"),
    )

    cantidad = models.DecimalField(

        _("Cantidad"),

        max_digits=10,

        decimal_places=2,

        default=1,

        validators=[
            MinValueValidator(0.01)
        ],
    )

    cantidad_recibida = models.DecimalField(
        _("Cantidad Recibida"),
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Cantidad recibida")
    )
    observacion = models.TextField(
        _("Observación"),
        blank=True,
        null=True,
        help_text=_("Observación sobre la recepción de este producto")
    )
    
    class Meta:

        verbose_name = _(
            "Producto de Compra"
        )

        verbose_name_plural = _(
            "Productos de Compra"
        )

        unique_together = [
            "compra",
            "producto",
        ]

    def __str__(self):

        return (
            f"{self.compra} - "
            f"{self.producto}"
        )

    # ======================================================
    # PRECIO UNITARIO
    # ======================================================

    @property
    def precio_unitario(self):

        if (
            self.producto
            and getattr(
                self.producto,
                "costo_unitario",
                None
            )
        ):

            return Decimal(
                self.producto.costo_unitario
            ).quantize(

                Decimal("0.01"),

                rounding=ROUND_HALF_UP
            )

        return Decimal("0.00")

    # ======================================================
    # SUBTOTAL
    # ======================================================

    @property
    def subtotal(self):

        return (

            self.cantidad
            * self.precio_unitario

        ).quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )


    @property
    def subtotal_recibido(self):
        """Subtotal basado en la cantidad recibida"""
        cantidad = self.cantidad_recibida if self.cantidad_recibida > 0 else self.cantidad
        return (cantidad * self.precio_unitario).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
    
# ==========================================================
# FUNCIÓN PARA UPLOAD DE PDF (FUERA DE LA CLASE)
# ==========================================================

def factura_upload_path(instance, filename):
    """Genera la ruta para guardar el PDF de la factura"""
    import re
    # Limpiar el nombre del archivo (eliminar caracteres especiales)
    nombre_limpio = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    return f'compra/factura/{nombre_limpio}'


# ==========================================================
# COMPRA
# ==========================================================

class Compra(models.Model):

    # ======================================================
    # ESTADOS
    # ======================================================

    ESTADO_CHOICES = [

        ("pendiente", _("Pendiente")),

        ("aprobado", _("Aprobado")),

        ("recibido", _("Recibido")),

        ("rechazado", _("Rechazado")),
    ]

    # ======================================================
    # IVA
    # ======================================================

    IVA_CHOICES = [

        (Decimal("10.00"), "10%"),

        (Decimal("5.00"), "5%"),

        (Decimal("0.00"), "0%"),
    ]

    # ======================================================
    # RELACIONES
    # ======================================================

    proveedor = models.ForeignKey(

        "proveedor.Proveedor",

        on_delete=models.CASCADE,

        verbose_name=_("Proveedor"),

        null=True,

        blank=True,
    )

    descripcion = models.TextField(

        _("Descripción"),

        blank=True,

        null=True,
    )

    productos = models.ManyToManyField(

        "insumo.Insumo",

        through="CompraProducto",

        verbose_name=_("Productos"),
    )

    # ======================================================
    # FECHAS
    # ======================================================

    fecha_emision = models.DateTimeField(

        _("Fecha emisión"),

        default=timezone.now,
    )

    fecha_entrega_esperada = models.DateField(

        _("Fecha entrega esperada"),

        default=default_fecha_entrega_esperada,
    )

    # ======================================================
    # ESTADO
    # ======================================================

    estado = models.CharField(

        _("Estado"),

        max_length=20,

        choices=ESTADO_CHOICES,

        default="pendiente",
    )

    # ======================================================
    # TOTALES
    # ======================================================

    descuento = models.DecimalField(

        _("Descuento"),

        max_digits=12,

        decimal_places=2,

        default=0,

        validators=[
            MinValueValidator(0)
        ],
    )

    iva_porcentaje = models.DecimalField(

        _("IVA %"),

        max_digits=5,

        decimal_places=2,

        choices=IVA_CHOICES,

        default=Decimal("10.00"),
    )

    subtotal_productos = models.DecimalField(

        _("Subtotal"),

        max_digits=15,

        decimal_places=2,

        default=0,
    )

    iva_monto = models.DecimalField(

        _("IVA"),

        max_digits=15,

        decimal_places=2,

        default=0,
    )

    total = models.DecimalField(

        _("Total"),

        max_digits=15,

        decimal_places=2,

        default=0,
    )


    CONDICION_PAGO_CHOICES = [
        ("contado", _("Contado")),
        ("credito", _("Crédito")),
    ]

    condicion_pago = models.CharField(
        _("Condición de Pago"),
        max_length=10,
        choices=CONDICION_PAGO_CHOICES,
        default="contado",
    )

    fecha_recepcion = models.DateField(
        _("Fecha recepción"),
        null=True,
        blank=True,
    )

    factura_pdf = models.FileField(
        _("Factura PDF"),
        upload_to='compra/factura/',
        null=True,
        blank=True,
    )

    observaciones_recepcion = models.TextField(
        _("Observaciones de recepción"),
        blank=True,
        null=True,
    )

    # ======================================================
    # ENTRADA ALMACEN
    # ======================================================

    entrada_almacen_generada = models.BooleanField(

        _("Entrada generada"),

        default=False,
    )

    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    # ======================================================
    # META
    # ======================================================

    class Meta:

        verbose_name = _(
            "Orden de Compra"
        )

        verbose_name_plural = _(
            "Órdenes de Compra"
        )

        ordering = (
            "-fecha_emision",
        )

        permissions = [

            (
                "ver_compras",
                "Puede ver compras"
            ),

            (
                "agregar_compras",
                "Puede agregar compras"
            ),

            (
                "editar_compras",
                "Puede editar compras"
            ),

            (
                "imprimir_compras",
                "Puede imprimir compras"
            ),

            (
                "recibir_compras",
                "Puede recibir compras"
            ),
        ]

    # ======================================================
    # STRING
    # ======================================================

    def __str__(self):

        return (
            f"Compra #{self.id} - "
            f"{self.proveedor}"
        )

    # ======================================================
    # CALCULAR SUBTOTAL
    # ======================================================

    def calcular_subtotal_productos(self):

        subtotal = Decimal("0.00")

        for detalle in self.detalles.all():

            subtotal += detalle.subtotal

        return subtotal.quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

    # ======================================================
    # BASE IMPONIBLE
    # ======================================================

    def calcular_base_imponible(self):

        base = max(

            self.calcular_subtotal_productos()
            - self.descuento,

            Decimal("0.00")
        )

        return base.quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

    # ======================================================
    # IVA
    # ======================================================

    def calcular_iva(self):

        base = self.calcular_base_imponible()

        return (

            base
            * (
                self.iva_porcentaje
                / Decimal("100")
            )

        ).quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

    # ======================================================
    # TOTAL
    # ======================================================

    def calcular_total(self):

        return (

            self.calcular_base_imponible()
            + self.calcular_iva()

        ).quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

    # ======================================================
    # ACTUALIZAR TOTALES
    # ======================================================

    def actualizar_totales(self):

        subtotal = Decimal("0.00")

        for detalle in self.detalles.all():

            subtotal += detalle.subtotal

        subtotal = subtotal.quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

        base = max(

            subtotal - self.descuento,

            Decimal("0.00")
        )

        iva = (

            base
            * (
                self.iva_porcentaje
                / Decimal("100")
            )

        ).quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

        total = (
            base + iva
        ).quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

        self.subtotal_productos = subtotal

        self.iva_monto = iva

        self.total = total

    @property
    def nombre_factura(self):
        """Devuelve solo el nombre del archivo sin la ruta"""
        if self.factura_pdf:
            import os
            # Obtener solo el nombre del archivo
            nombre = os.path.basename(self.factura_pdf.name)
            # Eliminar la parte del hash si existe (formato: nombre_hash.pdf)
            partes = nombre.rsplit('_', 1)
            if len(partes) > 1 and len(partes[1]) > 10 and '.' in partes[1]:
                # Si la última parte parece un hash, devolver la primera parte
                return partes[0] + '.' + partes[1].split('.')[-1]
            return nombre
        return ''

    # ======================================================
    # VALIDAR DIA MES
    # ======================================================

    def _validar_dia_mes(

        self,

        fecha,

        field_name
    ):

        max_dia = calendar.monthrange(
            fecha.year,
            fecha.month
        )[1]

        if (
            fecha.month == 2
            and fecha.day == 29
            and not calendar.isleap(
                fecha.year
            )
        ):

            raise ValidationError({

                field_name: _(
                    f"El año "
                    f"{fecha.year} "
                    f"no es bisiesto."
                )
            })

        if fecha.day > max_dia:

            raise ValidationError({

                field_name: _(
                    "Día inválido."
                )
            })


    # ======================================================
    # CLEAN
    # ======================================================

    def clean(self):

        super().clean()

        if self.pk:

            subtotal = (
                self.calcular_subtotal_productos()
            )

            if self.descuento > subtotal:

                raise ValidationError({

                    "descuento": _(
                        "El descuento "
                        "no puede ser "
                        "mayor al subtotal."
                    )
                })

        if self.fecha_entrega_esperada:

            hoy = date.today()

            if (
                self.fecha_entrega_esperada
                < hoy
            ):

                raise ValidationError({

                    "fecha_entrega_esperada": _(
                        "La fecha no puede "
                        "ser menor a hoy."
                    )
                })

            self._validar_dia_mes(

                self.fecha_entrega_esperada,

                "fecha_entrega_esperada"
            )

    # ======================================================
    # SAVE
    # ======================================================

    def save(self, *args, **kwargs):

        if (
            self.estado == "pendiente"
            and date.today()
            > self.fecha_entrega_esperada
        ):

            self.estado = "rechazado"

        super().save(*args, **kwargs)

    # ======================================================
    # BASE IMPONIBLE PROPERTY
    # ======================================================

    @property
    def base_imponible(self):

        return max(

            self.subtotal_productos
            - self.descuento,

            Decimal("0.00")

        ).quantize(

            Decimal("0.01"),

            rounding=ROUND_HALF_UP
        )

    # ======================================================
    # DIAS RESTANTES
    # ======================================================

    @property
    def dias_restantes(self):

        if self.fecha_entrega_esperada:

            return max(

                (
                    self.fecha_entrega_esperada
                    - date.today()
                ).days,

                0
            )

        return 0

    # ======================================================
    # TIENE PRODUCTOS
    # ======================================================

    @property
    def tiene_productos(self):

        return (
            self.pk
            and self.detalles.exists()
        )

    # ======================================================
    # ES EDITABLE
    # ======================================================

    @property
    def es_editable(self):

        return (
            self.estado == "pendiente"
        )

    # ======================================================
    # GENERAR ENTRADA
    # ======================================================

    def generar_entrada_almacen(

        self,

        _observacion=""
    ):

        if self.estado != "aprobado":

            raise ValidationError(

                _(
                    "Solo se pueden "
                    "recibir compras "
                    "aprobadas."
                )
            )

        if self.entrada_almacen_generada:

            raise ValidationError(

                _(
                    "Esta compra ya "
                    "fue recibida."
                )
            )

        self.entrada_almacen_generada = True

        self.estado = "recibido"

        self.save(

            update_fields=[

                "estado",

                "entrada_almacen_generada",
            ]
        )

        return True


# ==========================================================
# BITACORA
# ==========================================================

class BitacoraCompra(models.Model):

    compra = models.ForeignKey(

        Compra,

        on_delete=models.CASCADE,

        related_name="bitacora",
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    evento = models.CharField(
        max_length=120
    )

    detalle = models.TextField(

        blank=True,

        null=True,
    )

    usuario = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,
    )
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    class Meta:

        verbose_name = _(
            "Bitácora de Compra"
        )

        ordering = (
            "-fecha",
        )

    def __str__(self):

        return (
            f"[{self.fecha:%Y-%m-%d %H:%M}] "
            f"{self.evento} - "
            f"Compra #{self.compra_id}"
        )

    @staticmethod
    def registrar(

        compra,

        evento,

        detalle="",

        usuario=None
    ):

        return BitacoraCompra.objects.create(

            compra=compra,

            evento=str(evento),

            detalle=detalle,

            usuario=usuario,
        )
