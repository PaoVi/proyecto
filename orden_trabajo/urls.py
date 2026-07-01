from django.urls import path
from . import views

# Sin app_name
urlpatterns = [
    # Listado con prefijo claro
    path("ordenes-trabajo/", views.orden_trabajo_lista, name="orden_trabajo_lista"),
    path("orden/crear/", views.orden_trabajo_crear, name="orden_trabajo_crear"),
    path("orden/ver/<int:orden_id>/", views.orden_trabajo_ver, name="orden_trabajo_ver"),
    path("orden/editar/<int:orden_id>/", views.orden_trabajo_editar, name="orden_trabajo_editar"),
    path("orden/imprimir/<int:orden_id>/", views.orden_trabajo_imprimir, name="orden_trabajo_imprimir"),
    path("orden/<int:orden_id>/cambiar-estado/", views.orden_trabajo_cambiar_estado, name="orden_trabajo_cambiar_estado"),
    path("orden-trabajo/cambiar-estados/", views.orden_trabajo_cambiar_estados, name="orden_trabajo_cambiar_estados"),
    path('orden/editar-reanudado/<int:orden_id>/', views.orden_trabajo_editar_reanudado, name='orden_trabajo_editar_reanudado'),

    path("orden/<int:orden_id>/generar-factura/", views.generar_factura_desde_orden, name='generar_factura_desde_orden'),

    # Asignaciones
    path("orden/<int:orden_id>/asignar-empleado/", views.asignar_empleado, name="orden_trabajo_asignar_empleado"),
    path("orden/<int:orden_id>/liberar-empleado/<int:asignacion_id>/", views.liberar_empleado, name="orden_trabajo_liberar_empleado"),

    path('empleado/<int:empleado_id>/ordenes/', views.empleado_ordenes, name='empleado_ordenes'),

    path('servicio/<int:servicio_id>/finalizar/', views.orden_servicio_finalizar, name='orden_servicio_finalizar'),
    path('orden/<int:orden_id>/servicio/<int:servicio_orden_id>/iniciar-trabajo/', views.iniciar_trabajo_empleado, name='iniciar_trabajo_empleado'),
    path('registro-tiempo/<int:registro_id>/finalizar/', views.finalizar_trabajo_empleado, name='finalizar_trabajo_empleado'),
    path('api/tiempo-real/<int:empleado_id>/', views.obtener_tiempo_real_empleado, name='obtener_tiempo_real_empleado'),
    path('registro-tiempo/<int:registro_id>/pausar/', views.pausar_trabajo_empleado, name='pausar_trabajo_empleado'), 
    path('registro-tiempo/<int:registro_id>/reanudar/', views.reanudar_trabajo_empleado, name='reanudar_trabajo_empleado'),

    path('limpiar-todo-tiempo/', views.limpiar_todo_tiempo, name='limpiar_todo_tiempo'),

    path('empleado/<int:empleado_id>/ordenes/', views.empleado_ordenes, name='empleado_ordenes'),
    path('empleado/<int:empleado_id>/pagar-comision/', views.pagar_comision_empleado, name='pagar_comision_empleado'),
    path('empleado/<int:empleado_id>/comisiones/', views.empleado_comisiones_historial, name='empleado_comisiones_historial'),

    path('orden/<int:orden_id>/enviar-revision/', views.orden_enviar_revision, name='orden_enviar_revision'),
    path('orden/<int:orden_id>/revision/', views.orden_revision, name='orden_revision'),
    path('orden/<int:orden_id>/reanudar-rechazo/', views.orden_reanudar_desde_rechazo, name='orden_reanudar_desde_rechazo'),
    path('orden/<int:orden_id>/facturar-aprobado/', views.orden_facturar_desde_aprobado, name='orden_facturar_desde_aprobado'),

    # Búsquedas
    path('buscar-clientes-autocomplete/', views.buscar_clientes_autocomplete, name='buscar_clientes_autocomplete'),
    path('buscar-vehiculos-autocomplete/', views.buscar_vehiculos_autocomplete, name='buscar_vehiculos_autocomplete'),
]
