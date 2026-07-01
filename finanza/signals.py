# pylint: disable=no-member
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=unused-argument

from django.db.models.signals import (
    post_save,
    post_delete,
)
from django.dispatch import receiver

from factura.models import Factura
from compra.models import Compra

from .models import (
    Caja,
    MovimientoFinanciero,
)


# ==========================================================
# FACTURA -> INGRESO (delega a la función utilitaria en views)
# ==========================================================

@receiver(
    post_save,
    sender=Factura
)
def generar_ingreso_factura(
    sender,
    instance,
    created,
    **kwargs
):

    if not created:
        return

    from .views import crear_movimiento_factura

    crear_movimiento_factura(
        instance,
        usuario=None
    )


# ==========================================================
# COMPRA -> EGRESO (delega a la función utilitaria en views)
# ==========================================================

@receiver(
    post_save,
    sender=Compra
)
def generar_egreso_compra(
    sender,
    instance,
    created,
    **kwargs
):

    if not created:
        return

    from .views import crear_movimiento_compra

    crear_movimiento_compra(
        instance,
        usuario=None
    )


# ==========================================================
# RECALCULAR SALDO AL ELIMINAR MOVIMIENTO
# ==========================================================

@receiver(
    post_delete,
    sender=MovimientoFinanciero
)
def recalcular_saldo_al_eliminar(
    sender,
    instance,
    **kwargs
):

    caja = instance.caja

    ingresos = caja.total_ingresos
    egresos = caja.total_egresos

    caja.saldo_actual = (
        caja.monto_inicial
        + ingresos
        - egresos
    )

    caja.save(
        update_fields=[
            "saldo_actual"
        ]
    )
