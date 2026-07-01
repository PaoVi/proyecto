# urls.py

# pylint: disable=missing-module-docstring

from django.urls import path
from . import views

urlpatterns = [
    path('compras/',views.compra_lista,name='compra_lista'),
    path('compra/crear/',views.compra_crear,name='compra_crear'),
    path('compra/ver/<int:compra_id>/',views.compra_ver,name='compra_ver'),
    path('compra/editar/<int:compra_id>/',views.compra_editar,name='compra_editar'),
    path('compra/cambiar-estados/',views.compra_cambiar_estados,name='compra_cambiar_estados'),
    path('compra/<int:compra_id>/aprobar/',views.compra_aprobar,name='compra_aprobar'),
    path('compra/<int:compra_id>/rechazar/',views.compra_rechazar,name='compra_rechazar'),
    path('compra/<int:compra_id>/recibir/',views.compra_recibir,name='compra_recibir'),
    path('compra/imprimir/<int:compra_id>/',views.compra_imprimir,name='compra_imprimir'),
    path('compra/<int:compra_id>/recibir/', views.compra_recibir, name='compra_recibir'),
    path('compra/<int:compra_id>/cargar-factura/', views.compra_cargar_factura, name='compra_cargar_factura'),
    
    path('compra/<int:compra_id>/ver-pdf/', views.compra_ver_pdf, name='compra_ver_pdf'),
    path('buscar-proveedores/', views.buscar_proveedores_autocomplete, name='buscar_proveedores_autocomplete'),
    path('buscar-insumos-compra/', views.buscar_insumos_compra, name='buscar_insumos_compra'),
]
