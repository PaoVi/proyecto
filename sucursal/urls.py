from django.urls import path
from . import views

app_name = 'sucursal'

urlpatterns = [
    path('sucursales/', views.sucursal_list, name='sucursal_list'),
    path('sucursales/nueva/', views.sucursal_create, name='sucursal_create'),
    path('sucursales/<int:pk>/editar/', views.sucursal_update, name='sucursal_update'),
    path('sucursales/<int:pk>/toggle/', views.sucursal_toggle, name='sucursal_toggle'),
    path('sucursales/set/<int:pk>/', views.set_sucursal, name='set_sucursal'),
]
