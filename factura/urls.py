from django.urls import path
from . import views

urlpatterns = [
    # FACTURACIÓN
    path('', views.factura_inicio, name='factura_inicio'),

    # FACTURAS
    path('facturas/', views.factura_lista, name='factura_lista'),
    path('factura/emitir/', views.factura_emitir, name='factura_emitir'),
    path('factura/ver/<int:factura_id>/', views.factura_ver, name='factura_ver'),
    path('factura/editar/<int:factura_id>/', views.factura_editar, name='factura_editar'),
    path('factura/anular/<int:factura_id>/', views.factura_anular, name='factura_anular'),

    path('factura/buscar-clientes/', views.buscar_clientes_autocomplete, name='buscar_clientes_autocomplete'),
    path('buscar-insumos-venta/', views.buscar_insumos_venta, name='buscar_insumos_venta'),
    # REIMPRESIÓN Y CONSULTA
    path('factura/imprimir/<int:factura_id>/', views.factura_imprimir, name='factura_imprimir'),
    path('factura/reimprimir/<int:factura_id>/', views.factura_reimprimir, name='factura_reimprimir'),
    path('factura/consultar/', views.factura_consultar, name='factura_consultar'),
    path('factura/<int:factura_id>/marcar-entregada/', views.factura_marcar_entregada, name='factura_marcar_entregada'),

    # NOTAS DE CRÉDITO
    path('nota-credito/emitir/<int:factura_id>/', views.nota_credito_emitir, name='nota_credito_emitir'),
    path('nota-credito/ver/<int:nota_id>/', views.nota_credito_ver, name='nota_credito_ver'),
    path('nota-credito/lista/', views.nota_credito_lista, name='nota_credito_lista'),
    path('notas-credito/', views.nota_credito_lista, name='nota_credito_lista'),
    path('nota-credito/<int:nota_id>/anular/', views.nota_credito_anular, name='nota_credito_anular'),
    path('nota-credito/<int:nota_id>/imprimir/', views.nota_credito_imprimir, name='nota_credito_imprimir'),
    path('nota-credito/seleccionar/', views.nota_credito_factura, name='nota_credito_factura'),
]
