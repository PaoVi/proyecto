# pylint: disable=missing-module-docstring

from django.urls import path

from . import views

urlpatterns = [

    path("dashboard_finanza/", views.dashboard_finanza, name="dashboard_finanza"),
    path("movimientos/", views.movimiento_lista, name="movimiento_lista"),
    path("movimientos/nuevo/", views.movimiento_crear, name="movimiento_crear"),
    path("caja/", views.caja_lista, name="caja_lista"),
    path("caja/apertura/", views.caja_apertura, name="caja_apertura"),
    path("caja/<int:caja_id>/cerrar/", views.caja_cierre, name="caja_cierre"),
    path("caja/<int:caja_id>/imprimir/", views.caja_imprimir, name="caja_imprimir"),
    path("cuentas-cobrar/", views.cuentas_cobrar, name="cuentas_cobrar"),
    path("cobro/<int:cuenta_id>/crear/", views.cobro_crear, name="cobro_crear"),
    path("cuentas-pagar/", views.cuentas_pagar, name="cuentas_pagar"),
    path("pago-proveedor/<int:cuenta_id>/crear/", views.pago_proveedor_crear, name="pago_proveedor_crear"),
    path("gastos/", views.gasto_lista, name="gasto_lista"),
    path("gastos/crear/", views.gasto_crear, name="gasto_crear"),
    path("gastos/<int:gasto_id>/", views.gasto_detalle, name="gasto_detalle"),
    path("gastos/<int:gasto_id>/pagar/", views.gasto_pagar, name="gasto_pagar"),
    path("reportes/", views.reportes_financieros, name="reportes_financieros"),
    path("reportes/balance/", views.reporte_balance, name="reporte_balance"),
]
