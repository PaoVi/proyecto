# orden_trabajo/signals.py
from __future__ import annotations

from datetime import timezone
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.apps import apps
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import OrdenTrabajo, AsignacionOrden, OrdenServicio, RegistroTiempoReal
from .services import ControlCargaService, ComisionService, ValidacionAsignacionService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# 1) Auto-crear OT al aprobar/confirmar un Presupuesto
# ─────────────────────────────────────────────────────────
@receiver(post_save, sender='presupuesto.Presupuesto', weak=False, dispatch_uid="presup_auto_ot_v1")
def presupuesto_auto_genera_ot(sender, instance, created, **kwargs):
    """
    Al quedar 'aprobado' o 'confirmado', crear OT si no existe.
    """
    try:
        estado = (instance.estado or "").lower()
        if estado not in ("aprobado", "confirmado"):
            return

        OrdenTrabajo = apps.get_model('orden_trabajo', 'OrdenTrabajo')

        if OrdenTrabajo.objects.filter(presupuesto_origen=instance).exists():
            return

        def _crear_ot():
            try:
                OrdenServicio = apps.get_model('orden_trabajo', 'OrdenServicio')
                BitacoraOrden = apps.get_model('orden_trabajo', 'BitacoraOrden')

                ot = OrdenTrabajo.objects.create(
                    cliente=instance.cliente,
                    vehiculo=instance.vehiculo,
                    descripcion=_("Generada automáticamente al aprobar/confirmar el presupuesto"),
                    estado='pendiente',
                    presupuesto_origen=instance,
                )

                for ps in instance.presupuestoservicio_set.select_related('servicio'):
                    precio_base = getattr(ps.servicio, "precio_base", None) or Decimal('0.00')
                    OrdenServicio.objects.create(
                        orden=ot,
                        servicio=ps.servicio,
                        cantidad=ps.cantidad,
                        precio_unitario=precio_base,
                    )

                ot.actualizar_totales(save=True)
                BitacoraOrden.registrar(
                    ot,
                    _("Creación desde presupuesto"),
                    f"Presupuesto #{instance.id}",
                    usuario=None
                )
            except Exception as e:
                logger.exception("Error creando OT automática desde Presupuesto #%s: %s", instance.id, e)

        transaction.on_commit(_crear_ot)

    except Exception as e:
        logger.exception("Signal presupuesto_auto_genera_ot falló para Presupuesto #%s: %s", getattr(instance, "id", "?"), e)


# ─────────────────────────────────────────────────────────
# 2) Mantener totales de la OT cuando cambian sus servicios
# ─────────────────────────────────────────────────────────
@receiver(post_save, sender='orden_trabajo.OrdenServicio', weak=False, dispatch_uid="os_sync_totales_save_v1")
def _sync_totales_ot_save(sender, instance, **kwargs):
    try:
        instance.orden.actualizar_totales(save=True)
    except Exception as e:
        logger.exception("Error sincronizando totales (save) para OT #%s: %s", getattr(instance.orden, "id", "?"), e)


@receiver(post_delete, sender='orden_trabajo.OrdenServicio', weak=False, dispatch_uid="os_sync_totales_delete_v1")
def _sync_totales_ot_delete(sender, instance, **kwargs):
    try:
        instance.orden.actualizar_totales(save=True)
    except Exception as e:
        logger.exception("Error sincronizando totales (delete) para OT #%s: %s", getattr(instance.orden, "id", "?"), e)


# ─────────────────────────────────────────────────────────
# 3) Detectar cambios de estado para actualizar horas
# ─────────────────────────────────────────────────────────
@receiver(pre_save, sender=OrdenTrabajo)
def orden_trabajo_pre_save(sender, instance, **kwargs):
    """Antes de guardar: detectar cambios de estado para actualizar horas."""
    if not instance.pk:
        return
    
    try:
        old_instance = OrdenTrabajo.objects.get(pk=instance.pk)
        old_state = old_instance.estado
        new_state = instance.estado
        
        if old_state != new_state:
            instance._estado_anterior = old_state
            instance._estado_nuevo = new_state
    except OrdenTrabajo.DoesNotExist:
        pass


@receiver(post_save, sender=OrdenTrabajo)
def orden_trabajo_post_save(sender, instance, created, **kwargs):
    """Después de guardar: procesar cambio de estado si ocurrió."""
    if not created and hasattr(instance, '_estado_anterior'):
        ControlCargaService.actualizar_por_cambio_estado(
            orden=instance,
            estado_anterior=instance._estado_anterior,
            estado_nuevo=instance._estado_nuevo
        )
        delattr(instance, '_estado_anterior')
        delattr(instance, '_estado_nuevo')


# ─────────────────────────────────────────────────────────
# 4) Validar asignaciones antes de crear
# ─────────────────────────────────────────────────────────
@receiver(pre_save, sender=AsignacionOrden)
def asignacion_orden_pre_save(sender, instance, **kwargs):
    """Validar antes de crear/modificar una asignación."""
    if not instance.pk:
        valido, mensaje = ValidacionAsignacionService.validar_disponibilidad_empleado(
            empleado=instance.empleado,
            orden=instance.orden,
            servicio=instance.servicio
        )
        
        if not valido:
            raise ValidationError(mensaje)



@receiver(post_save, sender=RegistroTiempoReal)
def sync_empleado_finalizado(sender, instance, **kwargs):
    """Sincroniza empleado_finalizado cuando un registro de tiempo se finaliza"""
    if instance.estado == 'finalizado' and instance.servicio_orden:
        servicio_orden = instance.servicio_orden
        
        # Verificar si todos los empleados asignados tienen registros finalizados
        total_asignaciones = AsignacionOrden.objects.filter(
            servicio=servicio_orden
        ).count()
        
        registros_finalizados = RegistroTiempoReal.objects.filter(
            servicio_orden=servicio_orden,
            estado='finalizado'
        ).count()
        
        if total_asignaciones > 0 and registros_finalizados >= total_asignaciones:
            # Todos los empleados han finalizado
            if not servicio_orden.empleado_finalizado:
                servicio_orden.empleado_finalizado = True
                servicio_orden.fecha_finalizacion_empleado = timezone.now()
                servicio_orden.save(update_fields=['empleado_finalizado', 'fecha_finalizacion_empleado'])