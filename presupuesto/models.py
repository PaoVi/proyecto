from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.utils import timezone
from datetime import timedelta, date
import calendar
from servicio.models import Servicio


# Función para la fecha de vencimiento por defecto
def default_fecha_vencimiento():
    return (timezone.now() + timedelta(days=15)).date()

class PresupuestoServicio(models.Model):
    presupuesto = models.ForeignKey(
        'Presupuesto', 
        on_delete=models.CASCADE,
        verbose_name=_("Presupuesto")
    )
    servicio = models.ForeignKey(
        'servicio.Servicio', 
        on_delete=models.CASCADE,
        verbose_name=_("Servicio"),
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
            'invalid': _("Ingrese un número válido"),
            'min_value': _("Cantidad debe ser mayor a 0.00"),
        }
    )
    
    class Meta:
        verbose_name = _("Servicio del presupuesto")
        verbose_name_plural = _("Servicios del presupuesto")
        unique_together = ['presupuesto', 'servicio']

    def __str__(self):
        return f"{self.presupuesto} - {self.servicio}"

    @property
    def subtotal(self):
        """Calcula el subtotal del servicio: cantidad * precio_base del servicio"""
        if self.servicio and self.servicio.precio_base:
            subtotal = self.cantidad * self.servicio.precio_base
            return subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')

class Presupuesto(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', _('Pendiente')),
        ('aprobado', _('Aprobado')),
        ('rechazado', _('Rechazado')),
        ('vencido', _('Vencido')),
    ]

    IVA_CHOICES = [
        (10, '10% - Con IVA'),
        (5, '5% - Con IVA'),
        (0, '0% - Sin IVA'),
    ]

    cliente = models.ForeignKey(
        'cliente.Cliente',
        on_delete=models.CASCADE,
        verbose_name=_("Cliente"),
        error_messages={
            'null': _("Este campo es obligatorio."),
            'blank': _("Este campo es obligatorio."),
        }
    )

    vehiculo = models.ForeignKey(
        'vehiculo.Vehiculo',
        on_delete=models.CASCADE,
        verbose_name=_("Vehículo"),
        help_text=_("Seleccione un vehículo por chapa"),
        error_messages={
            'null': _("Este campo es obligatorio."),
            'blank': _("Este campo es obligatorio."),
        }
    )

    descripcion = models.TextField(
        _("Descripción"),
        blank=True, null=True,
        help_text=_("Descripción general del presupuesto")
    )

    servicios = models.ManyToManyField(
        'servicio.Servicio',
        through='PresupuestoServicio',
        verbose_name=_("Servicios a realizar")
    )

    fecha_creacion = models.DateTimeField(
        _("Fecha de creación"),
        auto_now_add=True
    )

    fecha_vencimiento = models.DateField(
        _("Fecha de vencimiento"),
        default=default_fecha_vencimiento
    )

    estado = models.CharField(
        _("Estado"),
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )

    descuento = models.DecimalField(
        _("Descuento"),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Monto de descuento en guaraníes")
    )

    iva_porcentaje = models.DecimalField(
        _("IVA %"),
        max_digits=5,
        decimal_places=2,
        choices=IVA_CHOICES,
        default=10,
        help_text=_("Porcentaje de IVA aplicable")
    )

    iva_monto = models.DecimalField(
        _("Monto IVA"),
        max_digits=15,
        decimal_places=2,
        default=0
    )

    subtotal_servicios = models.DecimalField(
        _("Subtotal servicios"),
        max_digits=15,
        decimal_places=2,
        default=0
    )

    total = models.DecimalField(
        _("Total"),
        max_digits=15,
        decimal_places=2,
        default=0
    )

    orden_trabajo = models.OneToOneField(
        'orden_trabajo.OrdenTrabajo', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Orden de trabajo generada"),
        related_name='presupuesto_asociado'
    )

    orden_trabajo_generada = models.BooleanField( 
        _("Orden de trabajo generada"),
        default=False,
        help_text=_("Indica si ya se generó una orden de trabajo desde este presupuesto")
    )
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )
    
    class Meta:
        verbose_name = _("Presupuesto")
        verbose_name_plural = _("Presupuestos")
        ordering = ("-fecha_creacion",)
        permissions = [
            ("gestionar_presupuestos", "Puede gestionar presupuestos"),
            ("ver_presupuestos", "Puede ver presupuestos"),
            ("agregar_presupuestos", "Puede registrar presupuestos"),
            ("editar_presupuestos", "Puede actualizar presupuestos"),
            ("cambiar_estado_presupuestos", "Puede cambiar estado de presupuestos"),
            ("imprimir_presupuestos", "Puede imprimir presupuestos"),
        ]

    def __str__(self):
        return f"Presupuesto #{self.id} - {self.cliente}"

    def calcular_subtotal_servicios(self):
        """Calcula el subtotal sumando todos los servicios"""
        subtotal = Decimal('0.00')
        for presupuesto_servicio in self.presupuestoservicio_set.all():
            subtotal += presupuesto_servicio.subtotal
        return subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calcular_base_imponible(self):
        """Calcula la base imponible (subtotal - descuento)"""
        subtotal = self.calcular_subtotal_servicios()
        base = max(subtotal - self.descuento, Decimal('0.00'))
        return base.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calcular_iva(self):
        """Calcula el monto de IVA"""
        base_imponible = self.calcular_base_imponible()
        iva = base_imponible * (self.iva_porcentaje / Decimal('100'))
        return iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calcular_total(self):
        """Calcula el total final"""
        base_imponible = self.calcular_base_imponible()
        iva = self.calcular_iva()
        total = base_imponible + iva
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    
    def actualizar_totales(self):
        """Actualiza todos los campos calculados en la base de datos"""
        try:
            # Solo calcular si el objeto ya tiene ID
            if self.pk:
                self.subtotal_servicios = self.calcular_subtotal_servicios()
                self.iva_monto = self.calcular_iva()
                self.total = self.calcular_total()
            else:
                # Si no tiene ID, establecer valores por defecto
                self.subtotal_servicios = Decimal('0.00')
                self.iva_monto = Decimal('0.00')
                self.total = Decimal('0.00')
        except Exception as e:
            # En caso de error, establecer valores por defecto
            self.subtotal_servicios = Decimal('0.00')
            self.iva_monto = Decimal('0.00')
            self.total = Decimal('0.00')

    def calcular_subtotal_servicios(self):
        """Calcula el subtotal sumando todos los servicios"""
        # Verificar que el objeto tenga ID antes de acceder a relaciones
        if not self.pk:
            return Decimal('0.00')
        
        subtotal = Decimal('0.00')
        for presupuesto_servicio in self.presupuestoservicio_set.all():
            subtotal += presupuesto_servicio.subtotal
        return subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def _validar_dia_mes(self, fecha, field_name):
        """Valida que el día sea válido para el mes"""
        max_dia_mes = calendar.monthrange(fecha.year, fecha.month)[1]

        if fecha.month == 2 and fecha.day == 29 and not calendar.isleap(fecha.year):
            raise ValidationError({
                field_name: _("El año %(year)s no es bisiesto; no se permite el 29 de febrero.") % {'year': fecha.year}
            })

        if fecha.day > max_dia_mes:
            if fecha.month == 2:
                raise ValidationError({
                    field_name: _("Febrero de %(year)s sólo tiene %(max)s días.") % {'year': fecha.year, 'max': max_dia_mes}
                })
            elif max_dia_mes == 30:
                raise ValidationError({
                    field_name: _("El mes ingresado solo tiene 30 días.")
                })
            else:
                raise ValidationError({
                    field_name: _("El mes ingresado solo tiene 31 días.")
                })

    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        # Solo validar descuento si el objeto existe y tiene servicios
        if self.pk:
            subtotal = self.calcular_subtotal_servicios()
            if self.descuento > subtotal:
                raise ValidationError({
                    'descuento': _('El descuento no puede ser mayor al subtotal de servicios.')
                })
        
        # Validar fecha de vencimiento
        if self.fecha_vencimiento:
            hoy = date.today()
            if self.fecha_vencimiento <= hoy:
                raise ValidationError({
                    'fecha_vencimiento': _('La fecha de vencimiento debe ser posterior a la fecha actual.')
                })
            
            # No puede ser más de 1 mes en el futuro
            max_fecha = hoy + timedelta(days=15)
            if self.fecha_vencimiento > max_fecha:
                raise ValidationError({
                    'fecha_vencimiento': _('La fecha de vencimiento no puede ser mayor a la fecha actual +15 días.')
                })
            
            # Validar día del mes
            self._validar_dia_mes(self.fecha_vencimiento, 'fecha_vencimiento')


    def save(self, *args, **kwargs):
        """Sobrescribir save para asegurar cálculos automáticos"""
    
        # Verificación de vencimiento
        if self.estado == 'pendiente' and date.today() > self.fecha_vencimiento:
            self.estado = 'vencido'

        # Si es un objeto nuevo, establecer valores por defecto
        if not self.pk:
            self.descuento = self.descuento.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Actualizar totales antes de guardar
        self.actualizar_totales()
        
        # Verificar vencimiento - SOLO SI ESTÁ EN PENDIENTE
        if self.estado == 'pendiente' and date.today() > self.fecha_vencimiento:
            self.estado = 'vencido'
        
        # Solo validar si el objeto ya existe (tiene pk) y NO estamos en proceso de edición
        # Para objetos nuevos, la validación se hará después de crear los servicios
        if self.pk:
            # Verificar si estamos en un contexto de edición (cuando los servicios aún no se han actualizado)
            # Si hay servicios existentes, confiar en la validación del formulario
            if not self.presupuestoservicio_set.exists():
                self.full_clean()
            else:
                # En edición, confiar en la validación del formulario que ya consideró servicios existentes + nuevos
                pass
        
        super().save(*args, **kwargs)


    @property
    def base_imponible(self):
        """Retorna la base imponible (subtotal - descuento)"""
        base = max(self.subtotal_servicios - self.descuento, Decimal('0.00'))
        return base.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def marca_modelo_vehiculo(self):
        """Retorna marca y modelo del vehículo"""
        if self.vehiculo:
            return f"{self.vehiculo.marca} {self.vehiculo.modelo}"
        return ""

    @property
    def dias_restantes(self):
        """Calcula los días restantes hasta el vencimiento"""
        if self.fecha_vencimiento:
            hoy = date.today()
            dias = (self.fecha_vencimiento - hoy).days
            return max(dias, 0)  # No mostrar días negativos
        return 0

    @property
    def tiene_servicios(self):
        """Verifica si el presupuesto tiene servicios"""
        # Para objetos existentes, verificar en la base de datos
        if self.pk:
            return self.presupuestoservicio_set.exists()
        
        # Para objetos nuevos, verificar en el contexto del formulario
        # Esto se llenará desde la vista cuando se creen los servicios
        return hasattr(self, '_servicios_temporales') and self._servicios_temporales

    @property
    def es_editable(self):
        """Verifica si el presupuesto se puede editar"""
        # No se puede editar si está rechazado o vencido
        return self.estado not in ['aprobado', 'rechazado', 'vencido']

    @property
    def verificar_vencimiento(self):
        """Verifica si el presupuesto debe marcarse como vencido"""
        if (self.estado == 'pendiente' and 
            date.today() >= self.fecha_vencimiento):
            self.estado = 'vencido'
            self.save(update_fields=['estado'])
            return True
        return False
    
    def generar_orden_trabajo(self, observacion: str = ""):
        """
        Genera una Orden de Trabajo a partir de este presupuesto aprobado
        """
        if self.estado != 'aprobado':
            raise ValidationError("Solo se pueden generar órdenes de trabajo desde presupuestos aprobados.")
        
        try:
            from orden_trabajo.models import OrdenTrabajo, OrdenServicio, BitacoraOrden
            
            # Crear la orden de trabajo
            ot = OrdenTrabajo.objects.create(
                cliente=self.cliente,
                vehiculo=self.vehiculo,
                descripcion=observacion or f"Generado desde Presupuesto #{self.id}",
                estado='pendiente',
                presupuesto_origen=self,
            )
            
            # Copiar los servicios del presupuesto a la orden
            for ps in self.presupuestoservicio_set.all():
                OrdenServicio.objects.create(
                    orden=ot,
                    servicio=ps.servicio,
                    cantidad=ps.cantidad,
                    precio_unitario=ps.servicio.precio_base or Decimal('0.00'),
                )
            
            # Actualizar totales
            ot.actualizar_totales(save=True)
            
            # Registrar en bitácora
            BitacoraOrden.registrar(ot, "Creación desde presupuesto", f"Presupuesto #{self.id}")
            
            return ot
            
        except ImportError as e:
            raise ValidationError(f"Error al importar modelos de orden de trabajo: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error al generar orden de trabajo: {str(e)}")


class BitacoraPresupuesto(models.Model):
    presupuesto = models.ForeignKey('presupuesto.Presupuesto', on_delete=models.CASCADE, related_name='bitacora')
    fecha = models.DateTimeField(_("Fecha"), auto_now_add=True)
    evento = models.CharField(_("Evento"), max_length=120)
    detalle = models.TextField(_("Detalle"), blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Usuario")
    )
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    class Meta:
        verbose_name = _("Bitácora de Presupuesto")
        verbose_name_plural = _("Bitácora de Presupuesto")
        ordering = ("-fecha",)

    def __str__(self):
        return f"[{self.fecha:%Y-%m-%d %H:%M}] {self.evento} - Presupuesto #{self.presupuesto_id}"

    @staticmethod
    def registrar(presupuesto, evento: str, detalle: str = "", usuario=None):
        return BitacoraPresupuesto.objects.create(presupuesto=presupuesto, evento=str(evento), detalle=detalle, usuario=usuario)