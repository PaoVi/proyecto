from django.contrib import admin
from .models import Vehiculo

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("nro_chapa", "marca", "modelo", "anio", "tipo_combustible", "uso", "cedula_verde")
    search_fields = ("nro_chapa", "nro_chasis", "marca", "modelo", "color")
    list_filter = ("tipo_combustible", "uso", "via_importacion", "procedencia", "tipo_transmision", "cedula_verde", "alarma", "gps")
