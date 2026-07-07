from django.contrib import admin
from .models import Sucursal


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ["nombre", "telefono", "activo", "establecimiento", "punto_emision"]
    list_filter = ["activo"]
    search_fields = ["nombre"]
