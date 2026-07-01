from django.urls import path
from . import views
 
urlpatterns = [
    path('clientes/', views.cliente_lista, name='cliente_lista'),
    path('cliente/crear/', views.cliente_crear, name='cliente_crear'),
    path('cliente/ver/<int:cliente_id>/', views.cliente_ver, name='cliente_ver'),
    path('cliente/editar/<int:cliente_id>/', views.cliente_editar, name='cliente_editar'),
    path('cliente/desactivar/<int:cliente_id>/', views.cliente_desactivar, name='cliente_desactivar'),
    
    path('cliente/buscar-vehiculos/', views.buscar_vehiculos_vincular, name='buscar_vehiculos_vincular'),

    path('cliente/<int:cliente_id>/vehiculos/', views.cliente_vehiculos, name='cliente_vehiculos'),
    path('cliente/<int:cliente_id>/vehiculos/vincular-vehiculo/', views.cliente_vincular_vehiculo, name='cliente_vincular_vehiculo'),
    path('cliente/<int:cliente_id>/vehiculos/eliminar-vinculacion/<int:vehiculo_id>/',  views.cliente_eliminar_vehiculo, name='cliente_eliminar_vehiculo'),
    
    path('cliente/<int:cliente_id>/presupuestos/', views.cliente_presupuestos, name='cliente_presupuestos'),
    path('cliente/<int:cliente_id>/ordenes/', views.cliente_ordenes, name='cliente_ordenes'),
    path('cliente/<int:cliente_id>/facturas/', views.cliente_facturas, name='cliente_facturas'),
]

