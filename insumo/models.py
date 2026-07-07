import re
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction


def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


class GrupoInsumo(models.TextChoices):
    INSUMO = 'insumo', _('INSUMO (Material de trabajo)')
    REPUESTO = 'repuesto', _('REPUESTO (Parte para reparación)')
    HERRAMIENTA = 'herramienta', _('HERRAMIENTA')
    LIMPIEZA_MANTENIMIENTO = 'limpieza_mantenimiento', _('LIMPIEZA Y MANTENIMIENTO')
    INSUMO_VENTA = 'insumo_venta', _('INSUMO PARA VENTA')


class Insumo(models.Model):
    class Unidad(models.TextChoices):
        UN = "UN", _("UNIDAD")
        KG = "KG", _("KILOGRAMO")
        LT = "LT", _("LITRO")
        MT = "MT", _("METRO")
        CJ = "CJ", _("CAJA")
        PA = "PA", _("PAR")
        OT = "OT", _("OTRO")

    # ---- Campos principales ----
    nombre = models.CharField(
        _("Nombre"),
        max_length=150,
        unique=True,
        help_text=_("Ej.: Filtro de aceite, Aceite 10W40, Pastilla de freno…"),
    )
    descripcion = models.TextField(
        _("Descripción"),
        blank=True,
        help_text=_("Detalle breve del insumo."),
    )
    
    grupo = models.CharField(
        _("Grupo"),
        max_length=30,
        choices=GrupoInsumo.choices,
        default=GrupoInsumo.INSUMO,
        help_text=_("Clasificación principal del insumo"),
    )
    
    categoria = models.CharField(
        _("Categoría"),
        max_length=100,
        blank=True,
        help_text=_("Ej.: Lubricantes, Filtros, Frenos, Motor."),
    )
    unidad = models.CharField(
        _("Unidad"),
        max_length=2,
        choices=Unidad.choices,
        default=Unidad.UN,
    )
    
    # Inventario / costos
    costo_unitario = models.DecimalField(
        _("Costo unitario"),
        max_digits=14,
        decimal_places=2,
        help_text=_("Costo por unidad en Gs. (>= 0)."), 
    )
    stock_actual = models.DecimalField(
        _("Stock actual"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text=_("Cantidad disponible en inventario")
    )

    stock_minimo = models.DecimalField(
        _("Stock mínimo"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text=_("Cantidad mínima para alertas")
    )
    tiene_garantia = models.BooleanField(
        _("Tiene garantía"),
        default=False,
        help_text=_("Indica si este repuesto tiene garantía")
    )
    
    garantia_meses = models.PositiveIntegerField(
        _("Garantía (meses)"),
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text=_("Duración de la garantía en meses (1 a 12 meses)")
    )

    # Estado y trazabilidad
    is_active = models.BooleanField(_("Activo"), default=True)
    fecha_ingreso = models.DateTimeField(_("Fecha de ingreso"), auto_now_add=True)
    fecha_registro = models.DateTimeField(_("Fecha de registro"), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_("Última actualización"), auto_now=True)

    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    class Meta:
        verbose_name = _("Insumo")
        verbose_name_plural = _("Insumos")
        ordering = ("nombre",)
        permissions = [
            ("gestionar_insumos", "Puede gestionar insumos"),
            ("agregar_insumos", "Puede agregar insumos"),
            ("ver_insumos", "Puede ver insumos"),
            ("editar_insumos", "Puede actualizar insumos"),
            ("desactivar_insumos", "Puede desactivar/activar insumos"),
            ("gestionar_stock_insumos", "Puede gestionar el stock de insumos"),
        ]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["categoria"]),
            models.Index(fields=["grupo"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["tiene_garantia"]),
        ]

    @property
    def codigo_completo(self):
        """Genera el código en MAYÚSCULAS: INS-0001, REP-0001, etc."""
        prefijos = {
            'insumo': 'INS',
            'repuesto': 'REP',
            'herramienta': 'HER',
            'limpieza_mantenimiento': 'LYM',
            'insumo_venta': 'INSV',
        }
        prefijo = prefijos.get(self.grupo, 'INS')
        return f"{prefijo}-{self.id:04d}"

    @property
    def tiene_subinsumos(self):
        return self.subinsumos.exists()

    @property
    def stock_disponible_para_subinsumos(self):
        stock_en_subinsumos = self.subinsumos.filter(is_active=True).aggregate(
            total=models.Sum('stock_actual')
        )['total'] or 0
        return self.stock_actual - stock_en_subinsumos

    @property
    def stock_en_subinsumos(self):
        return self.subinsumos.filter(is_active=True).aggregate(
            total=models.Sum('stock_actual')
        )['total'] or 0

    @property
    def stock_fisico_real(self):
        return self.stock_actual

    @property
    def stock_libre(self):
        return self.stock_disponible_para_subinsumos

    def get_prefijo_codigo(self):
        """Retorna el prefijo en MAYÚSCULAS"""
        prefijos = {
            'insumo': 'INS',
            'repuesto': 'REP',
            'herramienta': 'HER',
            'limpieza_mantenimiento': 'LYM',
            'insumo_venta': 'INSV',
        }
        return prefijos.get(self.grupo, 'INS')

    def crear_subinsumos(self, cantidad, cantidad_por_subinsumo=1):
        """Crea subinsumos con código en MAYÚSCULAS: INS-0001-0001"""
        stock_total_necesario = cantidad * cantidad_por_subinsumo
        
        if stock_total_necesario > self.stock_disponible_para_subinsumos:
            raise ValidationError(
                _("No hay suficiente stock disponible. Stock libre: %(stock_libre)s, necesario: %(necesario)s") % {
                    'stock_libre': self.stock_disponible_para_subinsumos,
                    'necesario': stock_total_necesario
                }
            )
        
        subinsumos_creados = []
        
        ultimo_numero = self.subinsumos.aggregate(
            max_num=models.Max('numero')
        )['max_num'] or 0
        
        prefijo = self.get_prefijo_codigo()
        codigo_padre = f"{prefijo}-{self.id:04d}"
        
        with transaction.atomic():
            for i in range(1, cantidad + 1):
                numero_actual = ultimo_numero + i
                
                subinsumo = SubInsumo(
                    insumo_padre=self,
                    numero=numero_actual,
                    nombre=self.nombre,
                    stock_actual=cantidad_por_subinsumo,
                    is_active=True,
                    codigo_generado=f"{codigo_padre}-{numero_actual:04d}"
                )
                
                subinsumo.save()
                subinsumos_creados.append(subinsumo)
        
        return subinsumos_creados

    def puede_crear_subinsumos(self, cantidad, cantidad_por_subinsumo=1):
        stock_total_necesario = cantidad * cantidad_por_subinsumo
        stock_libre = self.stock_disponible_para_subinsumos
        
        if stock_total_necesario > stock_libre:
            return False, f"Stock insuficiente. Libre: {stock_libre}, Necesario: {stock_total_necesario}"
        
        return True, "OK"

    def delete(self, *args, **kwargs):
        self.subinsumos.all().delete()
        super().delete(*args, **kwargs)

    def desactivar_con_subinsumos(self):
        with transaction.atomic():
            self.subinsumos.update(is_active=False)
            self.is_active = False
            self.save()

    def __str__(self):
        return f"{self.codigo_completo} - {self.nombre} ({self.unidad})"

    @property
    def estado_stock(self):
        if self.stock_actual <= 0:
            return "agotado"
        elif self.stock_actual <= self.stock_minimo:
            return "bajo"
        else:
            return "normal"

    @property
    def valor_total(self) -> Decimal:
        q = self.stock_actual or Decimal("0")
        c = self.costo_unitario or Decimal("0")
        return q * c

    @property
    def cantidad(self) -> Decimal:
        return self.stock_actual or Decimal("0")

    def _normalize(self):
        self.nombre = _norm_spaces(self.nombre)
        self.categoria = _norm_spaces(self.categoria)
        self.unidad = (self.unidad or "").strip()
        if self.descripcion is not None:
            self.descripcion = self.descripcion.strip()

    def clean(self):
        super().clean()
        self._normalize()
    
        if self.categoria:
            self.categoria = self.categoria.upper()

        # VALIDACIÓN DE GARANTÍA
        if self.grupo == 'repuesto':
            if self.tiene_garantia:
                if not self.garantia_meses:
                    raise ValidationError({
                        'garantia_meses': _("Debe especificar la duración de la garantía en meses.")
                    })
                if self.garantia_meses < 1 or self.garantia_meses > 60:
                    raise ValidationError({
                        'garantia_meses': _("La garantía debe ser entre 1 y 60 meses.")
                    })
            else:
                # Si no tiene garantía, asegurar que garantia_meses sea None
                self.garantia_meses = None
        else:
            # Si no es repuesto, limpiar campos de garantía
            self.tiene_garantia = False
            self.garantia_meses = None

        if self.pk and not self.is_active:
            subinsumos_activos = self.subinsumos.filter(is_active=True)
            if subinsumos_activos.exists():
                raise ValidationError({
                    "is_active": _(
                        "No se puede desactivar este insumo porque tiene %(count)s sub-insumo(s) activo(s). "
                        "Primero debe desactivar o consumir todos los sub-insumos."
                    ) % {'count': subinsumos_activos.count()}
                })

        if self.stock_actual is not None and self.stock_actual < 0:
            raise ValidationError({"stock_actual": _("El stock actual no puede ser negativo.")})

        if self.stock_minimo is not None and self.stock_minimo < 0:
            raise ValidationError({"stock_minimo": _("El stock mínimo no puede ser negativo.")})

        if self.costo_unitario is not None and self.costo_unitario < 0:
            raise ValidationError({"costo_unitario": _("El costo no puede ser negativo.")})
        
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SubInsumo(models.Model):
    """Modelo para subinsumos"""
    
    insumo_padre = models.ForeignKey(
        Insumo,
        on_delete=models.CASCADE,
        related_name='subinsumos',
        verbose_name=_("Insumo padre")
    )
    
    numero = models.PositiveIntegerField(
        _("Número de subinsumo"),
        validators=[MinValueValidator(1)],
        help_text=_("Número secuencial para subinsumos (1, 2, 3, ...)")
    )
    
    codigo_generado = models.CharField(
        _("Código generado"),
        max_length=50,
        blank=True,
        help_text=_("Código completo del subinsumo (ej: INS-0001-0001)")
    )
    
    nombre = models.CharField(
        _("Nombre"),
        max_length=150,
        help_text=_("Nombre del subinsumo (puede ser igual al padre)")
    )
    descripcion = models.TextField(
        _("Descripción"),
        blank=True,
        help_text=_("Detalle breve del sub-insumo."),
    )

    stock_actual = models.DecimalField(
        _("Stock actual"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=1,
        help_text=_("Cantidad disponible para este subinsumo")
    )
    
    is_active = models.BooleanField(_("Activo"), default=True)
    fecha_creacion = models.DateTimeField(_("Fecha de creación"), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_("Última actualización"), auto_now=True)

    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    class Meta:
        verbose_name = _("SubInsumo")
        verbose_name_plural = _("SubInsumos")
        ordering = ["insumo_padre", "numero"]
        constraints = [
            models.UniqueConstraint(
                fields=['insumo_padre', 'numero'],
                name='unique_subinsumo_number'
            )
        ]
        indexes = [
            models.Index(fields=['insumo_padre', 'numero']),
            models.Index(fields=['codigo_generado']),
            models.Index(fields=['is_active']),
        ]

    @property
    def codigo_completo(self):
        if self.codigo_generado:
            return self.codigo_generado
        prefijo = self.insumo_padre.get_prefijo_codigo()
        return f"{prefijo}-{self.insumo_padre.id:04d}-{self.numero:04d}"

    @property
    def unidad(self):
        return self.insumo_padre.unidad

    @property
    def categoria(self):
        return self.insumo_padre.categoria

    @property
    def costo_unitario(self):
        return self.insumo_padre.costo_unitario

    def __str__(self):
        return f"{self.codigo_completo} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo_generado and self.insumo_padre_id:
            prefijo = self.insumo_padre.get_prefijo_codigo()
            self.codigo_generado = f"{prefijo}-{self.insumo_padre.id:04d}-{self.numero:04d}"
        super().save(*args, **kwargs)

    def clean(self):
        if self.insumo_padre and self.numero:
            qs = SubInsumo.objects.filter(
                insumo_padre=self.insumo_padre,
                numero=self.numero
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    'numero': _('Ya existe un subinsumo con este número para el insumo padre seleccionado.')
                })

        stock_actual_anterior = 0
        if self.pk:
            stock_actual_anterior = SubInsumo.objects.get(pk=self.pk).stock_actual
        
        stock_necesario_neto = self.stock_actual - stock_actual_anterior
        
        if stock_necesario_neto > 0 and stock_necesario_neto > self.insumo_padre.stock_disponible_para_subinsumos:
            raise ValidationError({
                'stock_actual': _('No hay suficiente stock disponible en el insumo padre.')
            })


# CONTROL DE STOCK
class MovimientoStock(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]
    
    MOTIVO_CHOICES = [
        ('compra', 'Compra'),
        ('ajuste', 'Ajuste de inventario'),
        ('produccion', 'Producción'),
        ('venta', 'Venta/Servicio'),
        ('danado', 'Dañado/Perdido'),
        ('devolucion', 'Devolución'),
        ('otros', 'Otros'),
    ]

    insumo = models.ForeignKey(
        Insumo, 
        on_delete=models.CASCADE,
        verbose_name=_("Insumo")
    )
    tipo = models.CharField(
        _("Tipo de movimiento"),
        max_length=10,
        choices=TIPO_CHOICES
    )
    cantidad = models.DecimalField(
        _("Cantidad"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    motivo = models.CharField(
        _("Motivo"),
        max_length=20,
        choices=MOTIVO_CHOICES,
        default='ajuste'
    )
    observaciones = models.TextField(
        _("Observaciones"),
        blank=True,
        null=True,
        help_text=_("Detalles adicionales del movimiento")
    )
    stock_anterior = models.DecimalField(
        _("Stock anterior"),
        max_digits=10,
        decimal_places=2
    )
    stock_posterior = models.DecimalField(
        _("Stock posterior"),
        max_digits=10,
        decimal_places=2
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_("Usuario")
    )
    fecha_movimiento = models.DateTimeField(
        _("Fecha de movimiento"),
        auto_now_add=True
    )
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    class Meta:
        verbose_name = _("Movimiento de stock")
        verbose_name_plural = _("Movimientos de stock")
        ordering = ("-fecha_movimiento",)

    def __str__(self):
        return f"{self.insumo.nombre} - {self.tipo} - {self.cantidad}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.stock_anterior = self.insumo.stock_actual
            
            if self.tipo == 'entrada':
                self.stock_posterior = self.stock_anterior + self.cantidad
            else:
                self.stock_posterior = self.stock_anterior - self.cantidad
            
            self.insumo.stock_actual = self.stock_posterior
            self.insumo.save()
        
        super().save(*args, **kwargs)