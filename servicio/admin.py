from django.contrib import admin
from .models import Servicio

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "mano_obra", "tiempo_min_estimado", "is_active", "fecha_registro")
    list_filter  = ("categoria", "is_active")
    search_fields = ("nombre", "categoria", "descripcion")
    ordering = ("nombre",)
