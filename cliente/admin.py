from django.contrib import admin
from .models import Cliente, NotificacionCliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'numero_documento',
        'tipo_documento',
        'tipo_cliente',      
        'nombre',
        'telefono',
        'email',
        'fecha_nacimiento',      
        'fecha_constitucion',   
        'is_active',
        'fecha_registro',
    )
    list_filter = (
        'tipo_documento',
        'tipo_cliente',         
        'is_active',
        'fecha_registro',
    )
    search_fields = ('numero_documento', 'nombre', 'email', 'telefono')
    ordering = ('-fecha_registro',)
    

@admin.register(NotificacionCliente)
class NotificacionClienteAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'email_activo', 'creado_en', 'actualizado_en')
    list_filter = ('email_activo',)
    search_fields = ('cliente__nombre', 'cliente__numero_documento')

 