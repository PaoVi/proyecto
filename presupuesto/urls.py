from django.urls import path
from . import views
 
urlpatterns = [
    path('presupuestos/', views.presupuesto_lista, name='presupuesto_lista'),
    path('presupuesto/crear/', views.presupuesto_crear, name='presupuesto_crear'),
    path('presupuesto/ver/<int:presupuesto_id>/', views.presupuesto_ver, name='presupuesto_ver'),
    path('presupuesto/editar/<int:presupuesto_id>/', views.presupuesto_editar, name='presupuesto_editar'),
    path('presupuesto/cambiar-estados/', views.presupuesto_cambiar_estados, name='presupuesto_cambiar_estados'),
    path('presupuesto/<int:presupuesto_id>/cambiar-estado/', views.presupuesto_cambiar_estado, name='presupuesto_cambiar_estado'),
    path('presupuesto/imprimir/<int:presupuesto_id>/', views.presupuesto_imprimir, name='presupuesto_imprimir'),
    
    path('presupuesto/<int:presupuesto_id>/generar-orden/', views.generar_orden_desde_presupuesto, name='generar_orden_desde_presupuesto'),
    
    path('presupuesto/vehiculos-cliente/<int:cliente_id>/', views.obtener_vehiculos_cliente, name='obtener_vehiculos_cliente'),
    path('presupuesto/buscar-clientes/', views.buscar_clientes_autocomplete, name='buscar_clientes_autocomplete'),
    path('presupuesto/buscar-vehiculos/', views.buscar_vehiculos_autocomplete, name='buscar_vehiculos_autocomplete'),
    
]
