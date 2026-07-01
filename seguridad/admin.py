from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'rol', 'is_active', 'fecha_creacion')
    list_filter = ('rol', 'is_active', 'fecha_creacion')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-fecha_creacion',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('rol', 'ultimo_acceso')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('rol',)
        }),
    )