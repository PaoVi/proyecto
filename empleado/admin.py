from django.contrib import admin
from .models import Empleado

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("id_empleado", "nombre", "cedula_ruc", "cargo", "ciudad", "estado", "fecha_registro")
    list_filter = ("estado", "cargo", "ciudad")
    search_fields = ("nombre", "cedula_ruc", "correo_electronico", "telefono")
    ordering = ("-fecha_registro",)