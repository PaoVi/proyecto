from django.urls import path
from . import views

urlpatterns = [
    # AUTENTICACIÓN
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.exit, name='exit'),
    
    # USUARIOS
    path('usuarios/', views.usuario_lista, name='usuario_lista'),
    path('usuario/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuario/ver/<int:usuario_id>/', views.usuario_ver, name='usuario_ver'),
    path('usuario/editar/<int:usuario_id>/', views.usuario_editar, name='usuario_editar'),
    path('usuario/desactivar/<int:usuario_id>/', views.usuario_desactivar, name='usuario_desactivar'),
    path('usuario/<int:usuario_id>/asignar-empleado/', views.usuario_asignar_empleado, name='usuario_asignar_empleado'),
    path('usuario/<int:usuario_id>/eliminar-empleado/', views.usuario_eliminar_empleado, name='usuario_eliminar_empleado'),
    path('usuario/buscar-empleados/', views.buscar_empleados_vincular, name='buscar_empleados_vincular'),
    
    # ROLES Y PERMISOS
    path('roles/', views.rol_lista, name='rol_lista'),
    path('rol/crear/', views.rol_crear, name='rol_crear'),
    path('rol/ver/<int:grupo_id>/', views.rol_ver, name='rol_ver'),
    path('rol/editar/<int:grupo_id>/', views.rol_editar, name='rol_editar'),
    path('rol/desactivar/<int:grupo_id>/', views.rol_desactivar, name='rol_desactivar'),

    # PERFILES DE USUARIO
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('perfil/editar/', views.perfil_usuario_editar, name='perfil_editar'),

    # CONFIGURACIONES DEL SISTEMA
    path('configuraciones/', views.configuracion_lista, name='configuracion_lista'),
    path('configuracion/crear/', views.configuracion_crear, name='configuracion_crear'),
    path('configuracion/ver/<int:config_id>/', views.configuracion_ver, name='configuracion_ver'),
    path('configuracion/editar/<int:config_id>/', views.configuracion_editar, name='configuracion_editar'),
    path('configuracion/desactivar/<int:config_id>/', views.configuracion_desactivar, name='configuracion_desactivar'),
    
    # NOTIFICACIONES
    path('config/email-remitente/', views.configuracion_email_notificaciones, name="configuracion_email_notificaciones"),
    
]