from django.urls import path
from . import views
 
urlpatterns = [
    path('servicios/', views.servicio_lista, name='servicio_lista'),
    path('servicio/crear/', views.servicio_crear, name='servicio_crear'),
    path('servicio/ver/<int:servicio_id>/', views.servicio_ver, name='servicio_ver'),
    path('servicio/editar/<int:servicio_id>/', views.servicio_editar, name='servicio_editar'),
    path('servicio/desactivar/<int:servicio_id>/', views.servicio_desactivar, name='servicio_desactivar'),
]
