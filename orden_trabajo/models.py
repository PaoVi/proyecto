from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db.models import Q, UniqueConstraint, Index
from django.conf import settings
from empleado.models import Empleado
from orden_trabajo.services import ComisionService


# Constantes de estados
ESTADOS_ORDEN = (
    ('pendiente', 'Pendiente'),
    ('espera_repuestos', 'Espera Repuestos'),
    ('en_proceso', 'En Proceso'),
    ('pausado', 'Pausado'),
    ('completado', 'Completado'),
    ('en_revision', 'En Revisión'),  
    ('aprobado', 'Aprobado'),        
    ('rechazado', 'Rechazado'),     
    ('facturado', 'Facturado'),
    ('cancelado', 'Cancelado'),
)
IVA_CHOICES = [
    (10, '10% - Con IVA'),
    (5, '5% - Con IVA'),
    (0, '0% - Sin IVA'),
]
ESTADOS_ASIGNACION = [
    ('asignado', _('Asignado')),
    ('en_ejecucion', _('En Ejecución')),
    ('liberado', _('Liberado')),
]

# Estados que no permiten edición
ESTADOS_BLOQUEADOS = ['facturado', 'cancelado']

# Transiciones permitidas entre estados
TRANSICIONES_PERMITIDAS = {
    'pendiente': ['espera_repuestos', 'en_proceso', 'cancelado'],
    'espera_repuestos': ['en_proceso', 'pausado', 'cancelado'],
    'en_proceso': ['espera_repuestos', 'pausado', 'completado', 'cancelado'],
    'pausado': ['espera_repuestos', 'en_proceso', 'cancelado'],
    'completado': ['en_revision'], 
    'en_revision': ['aprobado', 'rechazado'],  
    'aprobado': ['facturado'], 
    'rechazado': ['en_proceso'],  
    'facturado': [],
    'cancelado': [],
}



def quant2(value: Decimal) -> Decimal:
    if value is None:
        value = Decimal('0')
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class OrdenTrabajo(models.Model):
    cliente = models.ForeignKey('cliente.Cliente', on_delete=models.PROTECT, verbose_name=_("Cliente"))
    vehiculo = models.ForeignKey('vehiculo.Vehiculo', on_delete=models.PROTECT, verbose_name=_("Vehículo"))
    descripcion = models.TextField(_("Descripción / Observaciones"), blank=True, null=True)

    estado = models.CharField(_("Estado"), max_length=20, choices=ESTADOS_ORDEN, default='pendiente')
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

    presupuesto_origen = models.ForeignKey(
        'presupuesto.Presupuesto',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Presupuesto de origen"),
        related_name='ordenes_generadas',
        help_text=_("Se completa cuando la OT se genera desde un presupuesto confirmado"),
    )

    factura = models.OneToOneField(
        'factura.Factura',  
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orden_trabajo'
    )

    factura_generada = models.BooleanField( 
        _("Factura generada"),
        default=False,
        help_text=_("Indica si ya se generó una factura desde esta orden")
    )

    fecha_creacion = models.DateTimeField(_("Fecha de creación"), auto_now_add=True)
    fecha_inicio = models.DateTimeField(_("Fecha de inicio"), blank=True, null=True)
    fecha_fin = models.DateTimeField(_("Fecha de finalización"), blank=True, null=True)

    subtotal_servicios = models.DecimalField(_("Subtotal servicios"), max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(_("Total"), max_digits=15, decimal_places=2, default=0)

    servicios = models.ManyToManyField('servicio.Servicio', through='OrdenServicio', verbose_name=_("Servicios"))

    class Meta:
        verbose_name = _("Orden de Trabajo")
        verbose_name_plural = _("Órdenes de Trabajo")
        ordering = ("-fecha_creacion",)
        indexes = [
            Index(fields=["estado", "fecha_creacion"]),
            Index(fields=["fecha_creacion"]),
        ]
        permissions = [
            ("gestionar_ordenes_trabajo", "Puede gestionar órdenes de trabajo"),
            ("ver_ordenes_trabajo", "Puede ver órdenes de trabajo"),
            ("agregar_ordenes_trabajo", "Puede registrar órdenes de trabajo"),
            ("editar_ordenes_trabajo", "Puede actualizar órdenes de trabajo"),
            ("cambiar_estado_ordenes_trabajo", "Puede cambiar el estado de órdenes de trabajo"), 
            ("imprimir_ordenes_trabajo", "Puede imprimir órdenes de trabajo"),
        ]

    def __str__(self):
        return f"OT #{self.id} - {self.vehiculo} ({self.get_estado_display()})"


    @property
    def es_editable(self) -> bool:
        """Verifica si la orden se puede editar"""
        return self.estado not in ['completado', 'cancelado', 'facturado', 'aprobado', 'rechazado', 'en_revision']

    @property
    def marca_modelo_vehiculo(self):
        """Retorna marca y modelo del vehículo"""
        if self.vehiculo:
            return f"{self.vehiculo.marca} {self.vehiculo.modelo}"
        return ""

    @property
    def empleados_asignados(self):
        """Devuelve empleados únicos asignados a esta orden"""
        return Empleado.objects.filter(asignacionorden__orden=self).distinct()

    @property
    def base_imponible(self):
        """Calcula la base imponible (subtotal - descuento)"""
        base = max(self.subtotal_servicios - self.descuento, Decimal('0.00'))
        return quant2(base)
    
    # --- Cálculos ---
    def calcular_subtotal_servicios(self) -> Decimal:
        if not self.pk:
            return Decimal('0.00')
        subtotal = Decimal('0.00')
        for os in self.ordenservicio_set.all():
            subtotal += os.subtotal
        return quant2(subtotal)

    def calcular_iva(self) -> Decimal:
        """Calcula el monto de IVA basado en la base imponible"""
        base_imponible = self.base_imponible
        iva = base_imponible * (self.iva_porcentaje / Decimal('100'))
        return quant2(iva)

    def calcular_total(self) -> Decimal:
        """Calcula el total final (base imponible + IVA)"""
        base_imponible = self.base_imponible
        iva_monto = self.calcular_iva()
        total = base_imponible + iva_monto
        return quant2(total)

    def actualizar_totales(self, save: bool = False):
        """Actualiza todos los campos calculados"""
        self.subtotal_servicios = self.calcular_subtotal_servicios()
        self.iva_monto = self.calcular_iva()
        self.total = self.calcular_total()
        if save:
            super().save(update_fields=['subtotal_servicios', 'iva_monto', 'total'])

    # --- Métodos de estado ---
    def _validar_transicion_estado(self, nuevo_estado: str):
        """Valida si la transición de estado es permitida"""
        if self.estado in ESTADOS_BLOQUEADOS:
            raise ValidationError(
                f"No se puede modificar una orden en estado '{self.get_estado_display()}'."
            )
        
        if nuevo_estado not in TRANSICIONES_PERMITIDAS.get(self.estado, []):
            estados_permitidos = [self._get_estado_display(e) for e in TRANSICIONES_PERMITIDAS[self.estado]]
            raise ValidationError(
                f"No se puede cambiar de '{self.get_estado_display()}' "
                f"a '{self._get_estado_display(nuevo_estado)}'. "
                f"Transiciones permitidas: {', '.join(estados_permitidos)}"
            )

    def _get_estado_display(self, estado):
        """Obtener el display name del estado"""
        for codigo, display in ESTADOS_ORDEN:
            if codigo == estado:
                return display
        return estado

    def cambiar_estado(self, nuevo_estado: str):
        """Cambia el estado de la orden validando la transición"""
        if self.estado == nuevo_estado:
            return  # No hacer nada si es el mismo estado
        
        self._validar_transicion_estado(nuevo_estado)
        
        # Actualizar fechas según el estado
        if nuevo_estado == 'en_proceso' and not self.fecha_inicio:
            self.fecha_inicio = timezone.now()
        if nuevo_estado in ['completado', 'cancelado'] and not self.fecha_fin: 
            self.fecha_fin = timezone.now()
        
        self.estado = nuevo_estado
        self.save()

    def iniciar(self):
        """Inicia la orden (pendiente → en_proceso)"""
        self.cambiar_estado('en_proceso')

    def pausar(self):
        """Pausa la orden (en_proceso → pausado)"""  
        self.cambiar_estado('pausado')

    def reanudar(self):
        """Reanuda la orden (pausado → en_proceso)"""  
        self.cambiar_estado('en_proceso')

    def esperar_repuestos(self):
        """Pone la orden en espera de repuestos"""
        self.cambiar_estado('espera_repuestos')

    def completar(self):
        """Completa la orden y la prepara para revisión"""
        
        # Verificar que todos los servicios estén finalizados por empleados
        servicios = self.ordenservicio_set.all()
        
        if not servicios.exists():
            raise ValidationError("La orden no tiene servicios asignados")
        
        # Lista para almacenar servicios no finalizados con detalles
        servicios_no_finalizados = []
        servicios_sin_registro = []
        
        for servicio_orden in servicios:
            # Verificar si el servicio está marcado como finalizado por empleado
            if not servicio_orden.empleado_finalizado:
                # Verificar si hay registros de tiempo real para este servicio
                registros = RegistroTiempoReal.objects.filter(
                    servicio_orden=servicio_orden,
                    estado='finalizado'
                )
                
                if registros.exists():
                    # Tiene registros finalizados pero no está marcado - lo marcamos automáticamente
                    servicio_orden.empleado_finalizado = True
                    servicio_orden.fecha_finalizacion_empleado = timezone.now()
                    servicio_orden.save(update_fields=['empleado_finalizado', 'fecha_finalizacion_empleado'])
                else:
                    # No tiene registros finalizados
                    # Verificar si hay registros en curso o pausados
                    registros_activos = RegistroTiempoReal.objects.filter(
                        servicio_orden=servicio_orden,
                        estado__in=['en_curso', 'pausado']
                    )
                    
                    if registros_activos.exists():
                        servicios_no_finalizados.append({
                            'nombre': servicio_orden.servicio.nombre,
                            'estado': 'en_curso' if registros_activos.first().estado == 'en_curso' else 'pausado'
                        })
                    else:
                        servicios_sin_registro.append(servicio_orden.servicio.nombre)
        
        # Si hay servicios sin registrar o no finalizados, no se puede completar
        if servicios_sin_registro:
            raise ValidationError(
                f"Los siguientes servicios no han sido iniciados: {', '.join(servicios_sin_registro)}"
            )
        
        if servicios_no_finalizados:
            mensajes = []
            for s in servicios_no_finalizados:
                estado_texto = "en curso" if s['estado'] == 'en_curso' else "pausado"
                mensajes.append(f"{s['nombre']} ({estado_texto})")
            raise ValidationError(
                f"No se puede completar la orden. Los siguientes servicios no están finalizados: {', '.join(mensajes)}"
            )
        
        self.cambiar_estado('completado')

    def facturar(self):
        """Factura la orden y genera comisiones para los empleados"""
        
        if self.estado != 'aprobado':
            raise ValidationError("Solo las órdenes APROBADAS pueden facturarse")
        
        # Cambiar estado a facturado
        self.cambiar_estado('facturado')
        
        # Generar comisiones para los empleados al facturar
        ComisionService.procesar_comisiones_orden(self)
    
        return True

    def cancelar(self):
        """Cancela la orden"""
        self.cambiar_estado('cancelado') 

    # --- Validaciones ---
    def clean(self):
        super().clean()
        # Validar que tenga al menos un servicio si ya existe
        if self.pk and not self.ordenservicio_set.exists():
            raise ValidationError(_("La orden debe tener al menos un servicio."))

    def save(self, *args, **kwargs):
        # Recalcula totales antes de guardar
        self.actualizar_totales(save=False)
        # Normaliza centavos por coherencia
        self.subtotal_servicios = quant2(self.subtotal_servicios or Decimal('0'))
        self.iva_monto = quant2(self.iva_monto or Decimal('0'))
        self.total = quant2(self.total or Decimal('0'))
        super().save(*args, **kwargs)

    # --- Fabricación desde Presupuesto ---
    @classmethod
    def crear_desde_presupuesto(cls, presupuesto_obj, observacion: str = ""):
        """
        Crea una OT a partir de un Presupuesto aprobado/confirmado.
        Copia servicios con el precio vigente del servicio.
        """
        if getattr(presupuesto_obj, "estado", "").lower() not in ("aprobado", "confirmado"):
            raise ValidationError(_("El presupuesto no está confirmado/aprobado."))

        ot = cls.objects.create(
            cliente=presupuesto_obj.cliente,
            vehiculo=presupuesto_obj.vehiculo,
            descripcion=observacion,
            estado='pendiente',
            presupuesto_origen=presupuesto_obj,
            descuento=presupuesto_obj.descuento or Decimal('0.00'),
            iva_porcentaje=presupuesto_obj.iva_porcentaje or 10,
        )

        for ps in presupuesto_obj.presupuestoservicio_set.select_related('servicio'):
            OrdenServicio.objects.create(
                orden=ot,
                servicio=ps.servicio,
                cantidad=ps.cantidad,
                precio_unitario=ps.servicio.precio_base or Decimal('0.00'),
            )

        ot.actualizar_totales(save=True)
        BitacoraOrden.registrar(ot, _("Creación desde presupuesto"), f"Presupuesto #{presupuesto_obj.id}")
        return ot

    # --- Métodos de asignación ---
    def asignar_empleado(self, empleado, estado='asignado'):
        asignacion, created = AsignacionOrden.objects.get_or_create(
            orden=self, empleado=empleado, defaults={"estado": estado}
        )
        if not created:
            asignacion.estado = estado
            asignacion.save()
        return asignacion

    def liberar_asignacion(self, empleado):
        try:
            asign = AsignacionOrden.objects.get(orden=self, empleado=empleado, estado__in=['asignado', 'en_ejecucion'])
            asign.estado = 'liberado'
            asign.fecha_liberacion = timezone.now()
            asign.save()
            return asign
        except AsignacionOrden.DoesNotExist:
            return None

    # --- Revisión ---
    def enviar_a_revision(self):
        """Envía la orden completada a revisión"""
        if self.estado != 'completado':
            raise ValidationError("Solo las órdenes completadas pueden enviarse a revisión")
        
        # Crear registros de revisión para cada servicio (inicialmente sin aprobar)
        for servicio_orden in self.ordenservicio_set.all():
            RevisionServicio.objects.get_or_create(
                orden_servicio=servicio_orden,
                orden_trabajo=self,
                defaults={'aprobado': False}
            )
        
        self.cambiar_estado('en_revision')
        return True
    
    def aprobar_revision(self, usuario=None):
        """Aprueba la orden después de verificar todos los servicios"""
        if self.estado != 'en_revision':
            raise ValidationError("La orden no está en estado de revisión")
        
        # Verificar que todos los servicios estén aprobados
        revisiones_pendientes = RevisionServicio.objects.filter(
            orden_trabajo=self,
            aprobado=False
        ).exists()
        
        if revisiones_pendientes:
            raise ValidationError("No se puede aprobar: hay servicios rechazados o sin revisar")
        
        self.cambiar_estado('aprobado')
        BitacoraOrden.registrar(self, "Orden aprobada", "Todos los servicios fueron aprobados", usuario)
        return True
    
    def rechazar_revision(self, usuario=None):
        """Rechaza la orden y la devuelve a en_proceso solo para servicios rechazados"""
        if self.estado != 'en_revision':
            raise ValidationError("La orden no está en estado de revisión")
        
        # Verificar que haya al menos un servicio rechazado
        servicios_rechazados = RevisionServicio.objects.filter(
            orden_trabajo=self,
            aprobado=False
        ).exists()
        
        if not servicios_rechazados:
            raise ValidationError("No hay servicios rechazados para rechazar la orden")
        
        # Marcar los servicios rechazados como modificables
        for revision in RevisionServicio.objects.filter(orden_trabajo=self, aprobado=False):
            revision.orden_servicio.modificado_despues_rechazo = False
            revision.orden_servicio.save(update_fields=['modificado_despues_rechazo'])
        
        self.cambiar_estado('rechazado')
        BitacoraOrden.registrar(self, "Orden rechazada", "Uno o más servicios fueron rechazados", usuario)
        return True
    
    def reanudar_desde_rechazo(self, usuario=None):
        """
        Reanuda la orden desde estado rechazado a en_proceso
        Solo los servicios rechazados pueden ser modificados
        """
        if self.estado != 'rechazado':
            raise ValidationError("La orden no está en estado rechazado")
        
        self.cambiar_estado('en_proceso')
        BitacoraOrden.registrar(self, "Orden reanudada", "Se reanudó el trabajo sobre servicios rechazados", usuario)
        return True
    
    def aprobar_servicio(self, servicio_orden_id, usuario=None, observacion=""):
        """Aprueba un servicio específico en la revisión"""
        if self.estado != 'en_revision':
            raise ValidationError("Solo se pueden aprobar servicios en estado de revisión")
        
        revision, created = RevisionServicio.objects.get_or_create(
            orden_servicio_id=servicio_orden_id,
            orden_trabajo=self,
            defaults={'aprobado': True, 'observacion': observacion, 'revisado_por': usuario}
        )
        
        if not created and not revision.aprobado:
            revision.aprobado = True
            revision.observacion = observacion
            revision.revisado_por = usuario
            revision.save()
        
        BitacoraOrden.registrar(self, "Servicio aprobado", f"Servicio ID {servicio_orden_id}", usuario)
        return True
    
    def rechazar_servicio(self, servicio_orden_id, usuario=None, motivo=""):
        """Rechaza un servicio específico en la revisión"""
        if self.estado != 'en_revision':
            raise ValidationError("Solo se pueden rechazar servicios en estado de revisión")
        
        revision, created = RevisionServicio.objects.get_or_create(
            orden_servicio_id=servicio_orden_id,
            orden_trabajo=self,
            defaults={'aprobado': False, 'observacion': motivo, 'revisado_por': usuario}
        )
        
        if not created and revision.aprobado:
            revision.aprobado = False
            revision.observacion = motivo
            revision.revisado_por = usuario
            revision.save()
        
        BitacoraOrden.registrar(self, "Servicio rechazado", f"Motivo: {motivo}", usuario)
        return True
    
    @property
    def puede_facturarse(self):
        """Verifica si la orden puede ser facturada"""
        return self.estado == 'aprobado'
    
    @property
    def servicios_aprobados(self):
        """Retorna los servicios aprobados en la última revisión"""
        return RevisionServicio.objects.filter(
            orden_trabajo=self,
            aprobado=True
        ).values_list('orden_servicio_id', flat=True)
    
    @property
    def servicios_rechazados(self):
        """Retorna los servicios rechazados en la última revisión"""
        return RevisionServicio.objects.filter(
            orden_trabajo=self,
            aprobado=False
        ).values_list('orden_servicio_id', flat=True)
    
    @property
    def todos_servicios_aprobados(self):
        """Verifica si todos los servicios están aprobados"""
        revisiones_pendientes = RevisionServicio.objects.filter(
            orden_trabajo=self,
            aprobado=False
        ).exists()
        return not revisiones_pendientes

    @property
    def hay_trabajo_en_curso(self):
        """Verifica si hay algún empleado trabajando en esta orden actualmente"""
        from .models import RegistroTiempoReal
        return RegistroTiempoReal.objects.filter(
            orden_trabajo=self,
            estado='en_curso'
        ).exists()

    @property
    def trabajo_en_curso_info(self):
        """Retorna información del trabajo en curso en esta orden"""
        from .models import RegistroTiempoReal
        
        registro = RegistroTiempoReal.objects.filter(
            orden_trabajo=self,
            estado='en_curso'
        ).select_related('empleado', 'servicio_orden__servicio').first()
        
        if registro:
            return {
                'empleado': registro.empleado,
                'servicio': registro.servicio_orden.servicio if registro.servicio_orden else None,
                'inicio': registro.fecha_inicio
            }
        return None


class OrdenServicio(models.Model):
    orden = models.ForeignKey('orden_trabajo.OrdenTrabajo', on_delete=models.CASCADE, verbose_name=_("Orden"))
    servicio = models.ForeignKey('servicio.Servicio', on_delete=models.PROTECT, verbose_name=_("Servicio"))
    cantidad = models.DecimalField(
        _("Cantidad"), max_digits=10, decimal_places=2, default=1,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    precio_unitario = models.DecimalField(
        _("Precio unitario"), max_digits=15, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )

    empleado_finalizado = models.BooleanField(
        _("Finalizado por empleado"),
        default=False,
        help_text=_("Indica si el empleado marcó este servicio como finalizado")
    )
    
    fecha_finalizacion_empleado = models.DateTimeField(
        _("Fecha de finalización (empleado)"),
        null=True, blank=True
    )

    modificado_despues_rechazo = models.BooleanField(
        _("Modificado después de rechazo"),
        default=False,
        help_text=_("Indica si este servicio fue modificado luego de ser rechazado en revisión")
    )
    insumos_descontados = models.BooleanField(
        _("Insumos descontados"),
        default=False,
        help_text=_("Indica si ya se descontaron los insumos de este servicio del stock")
    )
    class Meta:
        verbose_name = _("Servicio de la orden")
        verbose_name_plural = _("Servicios de la orden")
        constraints = [
            UniqueConstraint(fields=['orden', 'servicio'], name='uq_orden_servicio'),
            models.CheckConstraint(check=Q(cantidad__gt=0), name="ck_os_cantidad_gt_0"),
            models.CheckConstraint(check=Q(precio_unitario__gte=0), name="ck_os_precio_gte_0"),
        ]
        indexes = [
            Index(fields=['orden']),
            Index(fields=['servicio']),
        ]

    def __str__(self):
        return f"{self.orden} - {self.servicio}"

    @property
    def subtotal(self) -> Decimal:
        return quant2(self.cantidad * (self.precio_unitario or Decimal('0')))

    def clean(self):
        super().clean()
        if self.cantidad is None or self.cantidad <= 0:
            raise ValidationError({"cantidad": _("La cantidad debe ser mayor a 0.")})
        if self.precio_unitario is None or self.precio_unitario < 0:
            raise ValidationError({"precio_unitario": _("El precio unitario no puede ser negativo.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        self.precio_unitario = quant2(self.precio_unitario or Decimal('0'))
        super().save(*args, **kwargs)
        self.orden.actualizar_totales(save=True)

    def delete(self, *args, **kwargs):
        orden = self.orden
        super().delete(*args, **kwargs)
        orden.actualizar_totales(save=True)

    @property
    def esta_aprobado(self):
        """Verifica si el servicio fue aprobado en la última revisión"""
        ultima_revision = self.revisiones.order_by('-fecha_revision').first()
        return ultima_revision.aprobado if ultima_revision else False
    
    @property
    def esta_rechazado(self):
        """Verifica si el servicio fue rechazado en la última revisión"""
        ultima_revision = self.revisiones.order_by('-fecha_revision').first()
        return not ultima_revision.aprobado if ultima_revision else False
    
    @property
    def puede_modificarse(self):
        """
        Un servicio puede modificarse si:
        - La orden está en estado 'rechazado' Y
        - Este servicio específico fue rechazado Y
        - No está bloqueado por aprobación
        """
        orden = self.orden
        if orden.estado != 'rechazado':
            return False
        
        ultima_revision = self.revisiones.order_by('-fecha_revision').first()
        if ultima_revision and not ultima_revision.aprobado:
            return True
        
        return False
    

class AsignacionOrden(models.Model):
    orden = models.ForeignKey(
        'orden_trabajo.OrdenTrabajo', on_delete=models.CASCADE,
        related_name='asignaciones', verbose_name=_("Orden")
    )
    empleado = models.ForeignKey(
        'empleado.Empleado', on_delete=models.PROTECT,
        related_name='asignaciones', verbose_name=_("Empleado")
    )
    registro_tiempo_real = models.OneToOneField(
        'RegistroTiempoReal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignacion'
    )
    servicio = models.ForeignKey(OrdenServicio, on_delete=models.CASCADE, null=True, blank=True)
    estado = models.CharField(_("Estado"), max_length=20, choices=ESTADOS_ASIGNACION, default='asignado')
    fecha_asignacion = models.DateTimeField(_("Fecha de asignación"), auto_now_add=True)
    fecha_liberacion = models.DateTimeField(_("Fecha de liberación"), blank=True, null=True)

    class Meta:
        verbose_name = _("Asignación de Orden")
        verbose_name_plural = _("Asignaciones de Orden")
        indexes = [Index(fields=['empleado', 'estado'])]

    def __str__(self):
        return f"{self.empleado} → {self.orden} ({self.get_estado_display()})"

    @property
    def activa(self) -> bool:
        return self.estado in ('asignado', 'en_ejecucion') and self.orden.estado in ('pendiente', 'en_proceso', 'espera_repuestos', 'pausado')


class RegistroTiempoReal(models.Model):
    """
    Registro de tiempo REAL trabajado por un empleado en un servicio específico.
    """
    empleado = models.ForeignKey(
        'empleado.Empleado', 
        on_delete=models.CASCADE, 
        verbose_name=_("Empleado")
    )
    orden_trabajo = models.ForeignKey(
        'OrdenTrabajo', 
        on_delete=models.CASCADE, 
        verbose_name=_("Orden de trabajo")
    )
    servicio_orden = models.ForeignKey(
        'OrdenServicio',
        on_delete=models.CASCADE,
        verbose_name=_("Servicio de orden"),
        null=True, blank=True
    )
    fecha_inicio = models.DateTimeField(
        _("Fecha/Hora de inicio"),
        null=True, blank=True
    )
    fecha_fin = models.DateTimeField(
        _("Fecha/Hora de fin"),
        null=True, blank=True
    )
    minutos_trabajados = models.PositiveIntegerField(
        _("Minutos trabajados"),
        default=0
    )
    estado = models.CharField(
        _("Estado"),
        max_length=20,
        choices=[
            ('en_curso', 'En curso'),
            ('finalizado', 'Finalizado'),
            ('pausado', 'Pausado')
        ],
        default='en_curso'
    )
    fecha_registro = models.DateTimeField(_("Fecha de registro"), auto_now_add=True)

    
    class Meta:
        verbose_name = _("Registro de tiempo real")
        verbose_name_plural = _("Registros de tiempo real")
        ordering = ("-fecha_inicio",)
    
    def __str__(self):
        return f"{self.empleado} - {self.orden_trabajo} - {self.get_estado_display()}"
    
    def iniciar_trabajo(self):
        """Marca el inicio del trabajo con la hora actual"""
        from django.utils import timezone
        self.fecha_inicio = timezone.now()
        self.estado = 'en_curso'
        self.save(update_fields=['fecha_inicio', 'estado'])
        return self
    
    def pausar_trabajo(self):
        """
        Pausa el trabajo y guarda los minutos acumulados hasta ahora
        """
        if self.estado == 'en_curso' and self.fecha_inicio:
            from django.utils import timezone
            delta = timezone.now() - self.fecha_inicio
            minutos_adicionales = int(delta.total_seconds() // 60)
            self.minutos_trabajados += minutos_adicionales
            self.estado = 'pausado'
            self.save(update_fields=['minutos_trabajados', 'estado'])
        return self

    def reanudar_trabajo(self):
        """
        Reanuda el trabajo después de una pausa.
        Actualiza la fecha_inicio al momento de reanudar.
        El tiempo acumulado (minutos_trabajados) se mantiene.
        """
        from django.utils import timezone
        self.fecha_inicio = timezone.now()
        self.estado = 'en_curso'
        self.save(update_fields=['fecha_inicio', 'estado'])
        return self

    def finalizar_trabajo(self):
        """
        Marca el fin del trabajo y calcula minutos trabajados totales
        """
        from django.utils import timezone
        self.fecha_fin = timezone.now()
        if self.fecha_inicio and self.estado == 'en_curso':
            delta = self.fecha_fin - self.fecha_inicio
            minutos_adicionales = int(delta.total_seconds() // 60)
            self.minutos_trabajados += minutos_adicionales
        self.estado = 'finalizado'
        self.save(update_fields=['fecha_fin', 'minutos_trabajados', 'estado'])
        return self

    @property
    def minutos_transcurridos(self):
        """
        Minutos transcurridos desde el inicio hasta ahora (si está en curso)
        Si ha sido pausado y reanudado, suma el tiempo acumulado + el tiempo desde la última reanudación
        """
        if self.estado == 'en_curso' and self.fecha_inicio:
            from django.utils import timezone
            delta = timezone.now() - self.fecha_inicio
            minutos_actuales = int(delta.total_seconds() // 60)
            return self.minutos_trabajados + minutos_actuales
        return self.minutos_trabajados

    @property
    def tiempo_formateado(self):
        """Retorna el tiempo trabajado en formato HH:MM"""
        minutos = self.minutos_transcurridos
        horas = minutos // 60
        mins = minutos % 60
        return f"{horas:02d}:{mins:02d}"
    

class RevisionServicio(models.Model):
    """Registro de revisión de cada servicio en una orden"""
    orden_servicio = models.ForeignKey(
        'OrdenServicio', 
        on_delete=models.CASCADE,
        related_name='revisiones',
        verbose_name=_("Servicio revisado")
    )
    orden_trabajo = models.ForeignKey(
        'OrdenTrabajo',
        on_delete=models.CASCADE,
        related_name='revisiones_servicios',
        verbose_name=_("Orden de trabajo")
    )
    aprobado = models.BooleanField(
        _("Aprobado"),
        default=False,
        help_text=_("True = aprobado, False = rechazado")
    )
    observacion = models.TextField(
        _("Observación"),
        blank=True,
        null=True,
        help_text=_("Motivo del rechazo o comentario de la revisión")
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Revisado por")
    )
    fecha_revision = models.DateTimeField(
        _("Fecha de revisión"),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _("Revisión de servicio")
        verbose_name_plural = _("Revisiones de servicios")
        unique_together = [['orden_servicio', 'orden_trabajo']]
    
    def __str__(self):
        estado = "Aprobado" if self.aprobado else "Rechazado"
        return f"{self.orden_servicio.servicio.nombre} - {estado}"
    

class BitacoraOrden(models.Model):
    orden = models.ForeignKey('orden_trabajo.OrdenTrabajo', on_delete=models.CASCADE, related_name='bitacora')
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

    class Meta:
        verbose_name = _("Bitácora de Orden")
        verbose_name_plural = _("Bitácora de Orden")
        ordering = ("-fecha",)

    def __str__(self):
        return f"[{self.fecha:%Y-%m-%d %H:%M}] {self.evento} - OT #{self.orden_id}"

    @staticmethod
    def registrar(orden, evento: str, detalle: str = "", usuario=None):
        return BitacoraOrden.objects.create(orden=orden, evento=str(evento), detalle=detalle, usuario=usuario)