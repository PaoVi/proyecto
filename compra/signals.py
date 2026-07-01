# pylint: disable=E1101,no-member
# pylint: disable=unused-argument
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

from django.db.models.signals import (
    post_save,
    post_delete,
)
from django.dispatch import receiver

from .models import (
    Compra,
    CompraProducto,
)


# ==========================================================
# RECALCULAR TOTALES
# ==========================================================

def _recalcular(compra_id):

    try:

        compra = Compra.objects.get(
            pk=compra_id
        )

        compra.actualizar_totales()

        compra.save(
            update_fields=[
                "subtotal_productos",
                "iva_monto",
                "total",
            ]
        )

    except Compra.DoesNotExist:

        pass


# ==========================================================
# GUARDAR DETALLE
# ==========================================================

@receiver(
    post_save,
    sender=CompraProducto
)
def detalle_guardado(
    sender,
    instance,
    **kwargs
):

    _recalcular(
        instance.compra_id
    )


# ==========================================================
# ELIMINAR DETALLE
# ==========================================================

@receiver(
    post_delete,
    sender=CompraProducto
)
def detalle_eliminado(
    sender,
    instance,
    **kwargs
):

    _recalcular(
        instance.compra_id
    )
