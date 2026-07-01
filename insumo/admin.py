from django.contrib import admin
from .models import Insumo

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "unidad", "costo_unitario", "stock_actual", "stock_minimo", "is_active", "fecha_ingreso")
    list_filter = ("is_active", "unidad")
    search_fields = ("nombre", "descripcion")
