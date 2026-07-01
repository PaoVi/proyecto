from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Factura, FacturaServicio, FacturaInsumo

def _recalc_factura_safe(factura_id: int):
    try:
        f = Factura.objects.get(pk=factura_id)
        f.recalcular_totales(guardar=True)
    except Factura.DoesNotExist:
        pass

@receiver(post_save, sender=FacturaServicio)
def _srv_saved(sender, instance, created, **kwargs):
    _recalc_factura_safe(instance.factura_id)

@receiver(post_delete, sender=FacturaServicio)
def _srv_deleted(sender, instance, **kwargs):
    _recalc_factura_safe(instance.factura_id)

@receiver(post_save, sender=FacturaInsumo)
def _ins_saved(sender, instance, created, **kwargs):
    _recalc_factura_safe(instance.factura_id)

@receiver(post_delete, sender=FacturaInsumo)
def _ins_deleted(sender, instance, **kwargs):
    _recalc_factura_safe(instance.factura_id)

@receiver(post_save, sender=Factura)
def _factura_saved(sender, instance, created, **kwargs):
    if instance.servicios.exists() or instance.insumos.exists():
        _recalc_factura_safe(instance.id)
