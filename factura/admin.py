from django.contrib import admin
from .models import Factura, FacturaServicio, FacturaInsumo


class FacturaServicioInline(admin.TabularInline):
    model = FacturaServicio
    extra = 1
    fields = ('descripcion', 'cantidad', 'precio_unitario', 'subtotal')
    readonly_fields = ('subtotal',)

    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = "Subtotal"


class FacturaInsumoInline(admin.TabularInline):
    model = FacturaInsumo
    extra = 1
    fields = ('descripcion', 'cantidad', 'precio_unitario', 'subtotal')
    readonly_fields = ('subtotal',)

    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = "Subtotal"


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = (
        'numero_formateado', 'fecha', 'iva', 'subtotal',
        'total_iva', 'total_general', 'estado', 'entregada'
    )
    list_filter = ('estado', 'iva', 'entregada', 'fecha')
    search_fields = (
        'establecimiento', 'punto_emision', 'numero', 'numero_ot', 'observaciones'
    )
    ordering = ('-fecha', '-id')

    readonly_fields = (
        'numero_formateado', 'total_iva', 'total_general', 'created_at', 'updated_at'
    )

    fieldsets = (
        ("Datos Generales", {
            'fields': (
                'establecimiento', 'punto_emision', 'numero', 'fecha', 'iva',
                'estado', 'entregada', 'configuracion_impresion'
            )
        }),
        ("Relación con OT", {
            'fields': ('sin_ot', 'numero_ot')
        }),
        ("Totales", {
            'fields': ('subtotal', 'total_iva', 'total_general')
        }),
        ("Observaciones", {
            'fields': ('observaciones',)
        }),
        ("Auditoría", {
            'classes': ('collapse',),
            'fields': ('numero_formateado', 'created_at', 'updated_at')
        }),
    )

    inlines = [FacturaServicioInline, FacturaInsumoInline]

    def save_model(self, request, obj, form, change):
        """Guarda y recalcula totales automáticamente."""
        super().save_model(request, obj, form, change)
        obj.recalcular_totales(guardar=True)

    def get_queryset(self, request):
        """Optimiza la consulta con prefetch de detalles."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('servicios', 'insumos')

