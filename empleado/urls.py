from django.urls import path
from . import views

urlpatterns = [
    path('empleados/', views.empleado_lista, name='empleado_lista'),
    path('empleado/crear/', views.empleado_crear, name='empleado_crear'),
    path('empleado/ver/<int:empleado_id>/', views.empleado_ver, name='empleado_ver'),
    path('empleado/editar/<int:empleado_id>/', views.empleado_editar, name='empleado_editar'),
    path('empleado/desactivar/<int:empleado_id>/', views.empleado_desactivar, name='empleado_desactivar'),

    path('empleado/buscar-usuarios/', views.buscar_usuarios_vincular, name='buscar_usuarios_vincular'),

    path('empleado/<int:empleado_id>/usuario/', views.empleado_usuario, name='empleado_usuario'),
    path('empleado/<int:empleado_id>/usuario/asignar-usuario/', views.empleado_asignar_usuario, name='empleado_asignar_usuario'),
    path('empleado/<int:empleado_id>/usuario/eliminar-usuario/', views.empleado_eliminar_usuario, name='empleado_eliminar_usuario'),
]