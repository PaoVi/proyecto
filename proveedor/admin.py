from django.contrib import admin
from .models import Proveedor, NotificacionProveedor

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = (
        'ruc',
        'razon_social',
        'nombre_fantasia',
        'telefono',
        'email',
        'ciudad',
        'direccion',
        'contacto_nombre',
        'contacto_telefono',
        'is_active',
        'fecha_registro',
    )
    list_filter = (
        'is_active',
        'fecha_registro',
    )
    search_fields = (
        'ruc',
        'razon_social',
        'telefono',
        'email',
        'contacto_nombre',
        'contacto_telefono',
    )
    ordering = ('-fecha_registro',)


@admin.register(NotificacionProveedor)
class NotificacionProveedorAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'email_activo', 'creado_en', 'actualizado_en')
    list_filter = ('email_activo',)
    search_fields = ('proveedor__razon_social', 'proveedor__ruc')
