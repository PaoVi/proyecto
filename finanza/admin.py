# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring

from django.contrib import admin

from .models import (
    Caja,
    MovimientoFinanciero,
    CuentaCobrar,
    CuentaPagar,
    Cobro,
    PagoProveedor,
)


# ==========================================================
# CAJA
# ==========================================================

@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):

    list_display = (

        "id",

        "fecha_apertura",

        "saldo_actual",

        "estado",
    )

    search_fields = (

        "id",
    )

    list_filter = (

        "estado",
    )

    ordering = (

        "-fecha_apertura",
    )


# ==========================================================
# MOVIMIENTOS
# ==========================================================

@admin.register(MovimientoFinanciero)
class MovimientoAdmin(admin.ModelAdmin):

    list_display = (

        "id",

        "tipo",

        "origen",

        "descripcion",

        "monto",

        "fecha",
    )

    list_filter = (

        "tipo",

        "origen",
    )

    search_fields = (

        "descripcion",
    )

    ordering = (

        "-fecha",
    )


# ==========================================================
# CUENTAS POR COBRAR
# ==========================================================

@admin.register(CuentaCobrar)
class CuentaCobrarAdmin(admin.ModelAdmin):

    list_display = (
    "factura",
    "cliente",
    "monto_total",
    "monto_pagado",
    "saldo_pendiente",
    "pagado",
    )

    list_filter = (

        "pagado",
    )

    search_fields = (

        "cliente__nombre",
    )


# ==========================================================
# CUENTAS POR PAGAR
# ==========================================================

@admin.register(CuentaPagar)
class CuentaPagarAdmin(admin.ModelAdmin):

    list_display = (
        "compra",
        "proveedor",
        "monto_total",
        "monto_pagado",
        "saldo_pendiente",
        "pagado",
    )

    list_filter = (

        "pagado",
    )

    search_fields = (

        "proveedor__razon_social",
    )
# ==========================================================
# COBROS
# ==========================================================

@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "cuenta",
        "fecha",
        "monto",
        "usuario",
    )

    list_filter = (
        "fecha",
    )

    ordering = (
        "-fecha",
    )


# ==========================================================
# PAGOS PROVEEDOR
# ==========================================================

@admin.register(PagoProveedor)
class PagoProveedorAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "cuenta",
        "fecha",
        "monto",
        "usuario",
    )

    list_filter = (
        "fecha",
    )

    ordering = (
        "-fecha",
    )
