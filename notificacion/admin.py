from django.contrib import admin
from .models import LogEnvio

@admin.register(LogEnvio)
class LogEnvioAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "tipo", "email", "referencia_id", "asunto", "exito")
    list_filter  = ("tipo", "exito", "creado_en")
    search_fields = ("email", "asunto", "detalle")
    ordering = ("-creado_en",)
