from django.urls import path
from . import views

urlpatterns = [
    path("insumos/", views.insumo_lista, name="insumo_lista"),
    path("insumo/crear/", views.insumo_crear, name="insumo_crear"),
    path("insumo/ver/<int:insumo_id>/", views.insumo_ver, name="insumo_ver"),
    path("insumo/editar/<int:insumo_id>/", views.insumo_editar, name="insumo_editar"),
    path("insumo/desactivar/<int:insumo_id>/", views.insumo_desactivar, name="insumo_desactivar"),
    path('insumo/<int:insumo_id>/crear-subinsumos/', views.insumo_crear_subinsumos, name='insumo_crear_subinsumos'),

    # Sub-Insumos
    path("subinsumos/", views.subinsumo_lista, name="subinsumo_lista"),
    path('stock/baja/confirmar-subinsumos/', views.stock_baja_confirmar_subinsumos, name='stock_baja_confirmar_subinsumos'),
    path('stock/baja/seleccionar-subinsumos/', views.stock_baja_seleccionar_subinsumos, name='stock_baja_seleccionar_subinsumos'),

    # Control de stock
    path('stock/', views.stock_control, name='stock_control'),
    path('stock/alta/', views.stock_alta, name='stock_alta'),
    path('stock/baja/', views.stock_baja, name='stock_baja'),
    path('stock/historial/', views.stock_historial, name='stock_historial'),
    path('stock/historial/<int:insumo_id>/', views.stock_historial, name='stock_historial_insumo'),
    path('stock/buscar-insumos/', views.buscar_insumos_movimiento, name='buscar_insumos_movimiento'),

    path('verificar-stock-servicio/<int:servicio_id>/', views.verificar_stock_servicio, name='verificar_stock_servicio'),
]
