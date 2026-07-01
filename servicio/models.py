from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import ROUND_HALF_UP, Decimal
import re

def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


class Servicio(models.Model):
    nombre = models.CharField(
        _("Nombre del servicio"),
        max_length=120,
        unique=True,
        help_text=_("Ej. Cambio de aceite, Alineación y balanceo")
    )

    descripcion = models.TextField(
        _("Descripción"),
        blank=True, null=True,
        help_text=_("Detalles breves del servicio.")
    )

    categoria = models.CharField(
        _("Categoría"),
        max_length=80,
        help_text=_("Ej. MANTENIMIENTO, FRENOS, MOTOR, ELECTRICIDAD")
    )

    mano_obra = models.DecimalField(
        _("Mano de obra"),
        max_digits=14,
        decimal_places=2,
        help_text=_("Monto en guaraníes. Debe ser mayor a 0.") 
    )

    tiempo_min_estimado = models.PositiveIntegerField(
        _("Tiempo mínimo estimado"),
        help_text=_("En minutos (Ej. 60 = 1 hora).")
    )

    comision_porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2,  # Ej: 15.50%
        default=10,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        blank=True,  # Permitir que sea opcional
        null=True,   # Permitir valores nulos
        help_text="Porcentaje de comisión para el empleado"
    )

    insumos = models.ManyToManyField(
        'insumo.Insumo',  
        through='ServicioInsumo', 
        verbose_name=_("Insumos requeridos")
    )

    costo_insumos = models.DecimalField(
        _("Costo total de insumos"),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Costo total calculado de todos los insumos")
    )

    is_active = models.BooleanField(_("Activo"), default=True)
    fecha_registro = models.DateTimeField(_("Fecha de registro"), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_("Fecha de actualización"), auto_now=True)

    class Meta:
        verbose_name = _("Servicio")
        verbose_name_plural = _("Servicios")
        ordering = ("nombre",)
        permissions = [
            ("gestionar_servicios", "Puede gestionar servicios"),
            ("ver_servicios", "Puede ver servicios"),
            ("agregar_servicios", "Puede registrar servicios"),
            ("editar_servicios", "Puede actualizar servicios"),
            ("desactivar_servicios", "Puede desactivar/activar servicios"),
        ]

    def __str__(self):
        return self.nombre

    @property
    def precio_base(self):
        """
        Calcula el precio base del servicio: mano_obra + costo_insumos
        """
        try:
            mano_obra = self.mano_obra if self.mano_obra else Decimal('0.00')
            costo_insumos = self.costo_insumos if self.costo_insumos else Decimal('0.00')
            
            precio = mano_obra + costo_insumos
            return Decimal(str(precio)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (TypeError, ValueError):
            return Decimal('0.00')
        
    def _normalize_simple_fields(self):
        if self.nombre:
            self.nombre = _norm_spaces(self.nombre)

        if self.categoria:
            # Convertir categoría a mayúsculas
            self.categoria = _norm_spaces(self.categoria.upper())

        if self.descripcion:
            self.descripcion = self.descripcion.strip()

    def clean(self):
        super().clean()
        self._normalize_simple_fields()

        if self.nombre:
            qs = Servicio.objects.filter(nombre__iexact=self.nombre)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"nombre": _("Ya existe un servicio con este nombre.")})

        if self.mano_obra is not None:
            if self.mano_obra < 0:
                raise ValidationError({"mano_obra": _("La mano de obra no puede ser negativo.")})
            if self.mano_obra == 0:
                raise ValidationError({"mano_obra": _("La mano de obra debe ser mayor a 0.")})

        if self.tiempo_min_estimado is not None:
            if self.tiempo_min_estimado < 1:
                raise ValidationError({"tiempo_min_estimado": _("El tiempo mínimo debe ser mayor a 00:00.")})
            if self.tiempo_min_estimado > 21600:
                raise ValidationError({"tiempo_min_estimado": _("El tiempo mínimo no puede exceder 360 horas (15 días).")})
            
        # Validar comisión_porcentaje si está presente
        if self.comision_porcentaje is not None:
            if self.comision_porcentaje < 0:
                raise ValidationError({"comision_porcentaje": _("El % de comisión no puede ser negativo.")})
            if self.comision_porcentaje > 100:
                raise ValidationError({"comision_porcentaje": _("El % de comisión no puede ser mayor a 100%.")})

    def actualizar_costo_insumos(self):
        try:
            from django.db.models import Sum, F
            
            # Usar aggregate para cálculo más eficiente en la base de datos
            resultado = self.servicioinsumo_set.filter(
                insumo__costo_unitario__isnull=False
            ).aggregate(
                total_costo=Sum(F('cantidad') * F('insumo__costo_unitario'))
            )
            
            total = resultado['total_costo'] or Decimal('0.00')
            
            # Redondear a 2 decimales
            self.costo_insumos = Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self.save(update_fields=['costo_insumos'])
            return self.costo_insumos
            
        except Exception as e:
            print(f"Error al actualizar costo de insumos: {e}")
            self.costo_insumos = Decimal('0.00')
            self.save(update_fields=['costo_insumos'])
            return self.costo_insumos

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def tiene_insumos(self):
        """Verifica si el servicio tiene insumos"""
        # Para objetos existentes, verificar en la base de datos
        if self.pk:
            return self.servicioinsumo_set.exists()
        
        # Para objetos nuevos, verificar en el contexto del formulario
        # Esto se llenará desde la vista cuando se creen los insumos
        return hasattr(self, '_insumos_temporales') and self._insumos_temporales
    

class ServicioInsumo(models.Model):
    servicio = models.ForeignKey('Servicio', on_delete=models.CASCADE)
    insumo = models.ForeignKey(
        'insumo.Insumo', 
        on_delete=models.CASCADE,
        error_messages={
        'null': _("Este campo es obligatorio."),
        'blank': _("Este campo es obligatorio."),
        }
    ) 
    cantidad = models.DecimalField(
        _("Cantidad"),
        max_digits=10, 
        decimal_places=2, 
        default=1,
        validators=[MinValueValidator(0.01)],
        error_messages={
            'required': _("Este campo es obligatorio."),
            'invalid':  _("Ingrese un número válido."),
            'min_value': _("Cantidad debe ser mayor a 0.00"),
        }
    )
    
    class Meta:
        verbose_name = _("Insumo del servicio")
        verbose_name_plural = _("Insumos del servicio")
        unique_together = ['servicio', 'insumo']

    def __str__(self):
        return f"{self.servicio} - {self.insumo}"

    @property
    def subtotal(self):
        if self.insumo.costo_unitario:
            return self.cantidad * self.insumo.costo_unitario
        return 0