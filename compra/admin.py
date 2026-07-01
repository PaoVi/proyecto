# pylint: disable=E1101,no-member,broad-exception-caught
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from .models import (
    Compra,
    CompraProducto,
)

# ==========================================================
# INLINE PRODUCTOS
# ==========================================================

class CompraProductoInline(admin.TabularInline):

    model = CompraProducto

    extra = 1

    min_num = 1

    verbose_name = "Producto"

    verbose_name_plural = "Productos"

    autocomplete_fields = [
        "producto"
    ]


# ==========================================================
# ACCION GENERAR ENTRADA
# ==========================================================

@admin.action(
    description=(
        "Generar Entrada "
        "de Almacén"
    )
)
def generar_entrada_almacen(

    _modeladmin,

    request,

    queryset
):

    compras_aprobadas = queryset.filter(

        estado="aprobado",

        entrada_almacen_generada=False
    )

    # ======================================================
    # VALIDAR SELECCION
    # ======================================================

    if compras_aprobadas.count() == 0:

        messages.error(

            request,

            _(
                "Seleccione compras "
                "aprobadas que "
                "no hayan sido "
                "recibidas aún."
            )
        )

        return

    if compras_aprobadas.count() > 1:

        messages.warning(

            request,

            _(
                "Seleccione solo "
                "una compra."
            )
        )

        return

    compra = compras_aprobadas.first()

    # ======================================================
    # GENERAR
    # ======================================================

    try:

        compra.generar_entrada_almacen()

        messages.success(

            request,

            _(
                f"Entrada generada "
                f"para la Compra "
                f"#{compra.id}."
            )
        )

        # ==================================================
        # REDIRECCIONAR SI EXISTE
        # ==================================================

        if hasattr(
            compra,
            "entrada_almacen"
        ) and compra.entrada_almacen:

            return HttpResponseRedirect(

                "/admin/almacen/"
                f"entradaalmacen/"
                f"{compra.entrada_almacen.id}/"
                "change/"
            )

    except Exception as exc:

        messages.error(

            request,

            _(
                f"Error: {str(exc)}"
            )
        )


# ==========================================================
# ADMIN COMPRA
# ==========================================================

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):

    list_display = [

        "id",

        "proveedor",

        "fecha_emision",

        "fecha_entrega_esperada",

        "estado",

        "subtotal_productos",

        "iva_monto",

        "total_formateado",

        "entrada_almacen_generada",
    ]

    list_filter = [

        "estado",

        "fecha_emision",
    ]

    search_fields = [

        "proveedor__nombre",

        "proveedor__ruc",
    ]

    readonly_fields = [

        "fecha_emision",
        "subtotal_productos",
        "iva_monto",
        "total",
    ]

    autocomplete_fields = [

        "proveedor",
    ]

    inlines = [
        CompraProductoInline
    ]

    actions = [
        generar_entrada_almacen
    ]

    list_per_page = 20

    date_hierarchy = "fecha_emision"

    ordering = [
        "-fecha_emision"
    ]

    # ======================================================
    # TOTAL FORMATEADO
    # ======================================================

    @admin.display(
        description="Total"
    )
    def total_formateado(
        self,
        obj
    ):

        return (
            f"Gs. "
            f"{obj.total:,.0f}"
        ).replace(",", ".")



