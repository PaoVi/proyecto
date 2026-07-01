from django.urls import path
from . import views


urlpatterns = [
    path("proveedores/", views.proveedor_lista, name="proveedor_lista"),
    path("proveedor/crear/", views.proveedor_crear, name="proveedor_crear"),
    path("proveedor/ver/<int:pk>/", views.proveedor_ver, name="proveedor_ver"),
    path("proveedor/editar/<int:pk>/", views.proveedor_editar, name="proveedor_editar"),
    path("proveedor/desactivar/<int:pk>/", views.proveedor_desactivar, name="proveedor_desactivar"),
]
