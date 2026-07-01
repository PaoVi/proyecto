from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import OrdenTrabajo, OrdenServicio, AsignacionOrden, BitacoraOrden


# Inlines
class OrdenServicioInline(admin.TabularInline):
    """Servicios dentro de la OT."""
    model = OrdenServicio
    extra = 0
    autocomplete_fields = ["servicio"]
    can_delete = True


class AsignacionOrdenInline(admin.TabularInline):
    """Asignaciones de empleados a la OT."""
    model = AsignacionOrden
    extra = 0
    autocomplete_fields = ["empleado"]
    can_delete = True


# Admin de OrdenTrabajo
@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    """Administrador de Órdenes de Trabajo con formato similar a Presupuestos."""
    
    list_display = ['id', 'cliente', 'marca_modelo_vehiculo', 'fecha_creacion', 'estado', 'total']
    list_filter = ['estado', 'fecha_creacion']
    search_fields = ['cliente__nombre', 'vehiculo__nro_chapa', 'vehiculo__marca', 'vehiculo__modelo']
    date_hierarchy = 'fecha_creacion'
    ordering = ('-fecha_creacion',)
    autocomplete_fields = ['cliente', 'vehiculo']
    list_select_related = ('cliente', 'vehiculo')
    inlines = [OrdenServicioInline, AsignacionOrdenInline]

    # Campos de solo lectura 
    readonly_fields = ['fecha_creacion', 'fecha_inicio', 'fecha_fin', 'subtotal_servicios', 'total']

    # Fieldsets organizados
    fieldsets = (
        (_("Información Básica"), {
            "fields": ("cliente", "vehiculo", "descripcion")
        }),
        (_("Estado y Fechas"), {
            "fields": ("estado", "fecha_creacion", "fecha_inicio", "fecha_fin")
        }),
        (_("Totales"), {
            "fields": ("subtotal_servicios", "total")
        }),
        (_("Origen"), {
            "fields": ("presupuesto_origen",),
            "classes": ("collapse",)
        }),
    )

    # Método para mostrar vehículo
    def marca_modelo_vehiculo(self, obj):
        if obj.vehiculo:
            return f"{obj.vehiculo.marca} {obj.vehiculo.modelo} - {obj.vehiculo.nro_chapa}"
        return "Sin vehículo"
    marca_modelo_vehiculo.short_description = 'Vehículo'
    marca_modelo_vehiculo.admin_order_field = 'vehiculo__marca'

    # ── Acciones para cambiar estado ──
    @admin.action(description=_("Marcar como 'En Proceso'"))
    def action_marcar_en_proceso(self, request, queryset):
        count = 0
        for ot in queryset:
            if ot.estado == "pendiente":
                ot.iniciar(user=request.user)
                count += 1
        if count:
            self.message_user(request, _(f"{count} orden(es) marcadas como 'En Proceso'."))

    @admin.action(description=_("Finalizar órdenes seleccionadas"))
    def action_finalizar(self, request, queryset):
        count = 0
        for ot in queryset:
            if ot.estado == "en_proceso":
                ot.finalizar(user=request.user)
                count += 1
        if count:
            self.message_user(request, _(f"{count} orden(es) finalizadas."))

    @admin.action(description=_("Cancelar órdenes seleccionadas"))
    def action_cancelar(self, request, queryset):
        count = 0
        for ot in queryset:
            if ot.estado in ("pendiente", "en_proceso"):
                ot.cancelar(user=request.user)
                count += 1
        if count:
            self.message_user(request, _(f"{count} orden(es) canceladas."))

    actions = ["action_marcar_en_proceso", "action_finalizar", "action_cancelar"]


# Admin de Bitácora
@admin.register(BitacoraOrden)
class BitacoraOrdenAdmin(admin.ModelAdmin):
    """Historial de eventos y cambios en las órdenes."""
    list_display = ("orden", "fecha", "evento", "usuario")
    list_filter = ("fecha", "evento")
    search_fields = ("orden__id", "evento", "detalle")
    date_hierarchy = "fecha"
    ordering = ("-fecha",)
    list_select_related = ("orden", "usuario")
    readonly_fields = ("orden", "fecha", "evento", "usuario", "detalle")