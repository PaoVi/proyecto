from django.urls import path
from . import views

urlpatterns = [
    path('vehiculos/', views.vehiculo_lista, name='vehiculo_lista'),
    path('vehiculo/crear/', views.vehiculo_crear, name='vehiculo_crear'),
    path('vehiculo/ver/<int:vehiculo_id>/', views.vehiculo_ver, name='vehiculo_ver'),
    path('vehiculo/editar/<int:vehiculo_id>/', views.vehiculo_editar, name='vehiculo_editar'),
    path('vehiculo/desactivar/<int:vehiculo_id>/', views.vehiculo_desactivar, name='vehiculo_desactivar'),

    path('vehiculo/buscar-clientes/', views.buscar_clientes_vincular, name='buscar_clientes_vincular'),

    path('vehiculo/<int:vehiculo_id>/propietarios/', views.vehiculo_propietarios, name='vehiculo_propietarios'),
    path('vehiculos/<int:vehiculo_id>/propietarios/vincular-cliente/', views.vehiculo_vincular_cliente, name='vehiculo_vincular_cliente'),
    path('vehiculo/<int:vehiculo_id>/propietarios/eliminar-cliente/', views.vehiculo_eliminar_cliente, name='vehiculo_eliminar_cliente'),
    path('vehiculo/<int:vehiculo_id>/presupuestos/', views.vehiculo_presupuestos, name='vehiculo_presupuestos'),

    path('vehiculos/ingreso/', views.vehiculo_ingreso_lista, name='vehiculo_ingreso_lista'),
    path('vehiculos/ingreso/crear/', views.vehiculo_ingreso_crear, name='vehiculo_ingreso_crear'),    
]