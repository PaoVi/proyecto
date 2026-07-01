from django.contrib import admin
from .models import Presupuesto, PresupuestoServicio
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

class PresupuestoServicioInline(admin.TabularInline):
    model = PresupuestoServicio
    extra = 1

@admin.action(description="Generar Orden de Trabajo para presupuestos seleccionados")
def generar_orden_trabajo(modeladmin, request, queryset):
    # Filtrar solo presupuestos aprobados
    presupuestos_aprobados = queryset.filter(estado='aprobado')
    
    if presupuestos_aprobados.count() == 0:
        messages.error(request, _("Solo se pueden generar órdenes de trabajo desde presupuestos aprobados."))
        return
    
    # Si solo hay uno, redirigir directamente a crear la OT
    if presupuestos_aprobados.count() == 1:
        presupuesto = presupuestos_aprobados.first()
        try:
            ot = presupuesto.generar_orden_trabajo()
            messages.success(request, _(f"Orden de Trabajo #{ot.id} generada exitosamente."))
            # Redirigir a la orden de trabajo creada
            return HttpResponseRedirect(f'/admin/orden_trabajo/ordentrabajo/{ot.id}/change/')
        except Exception as e:
            messages.error(request, _(f"Error al generar orden de trabajo: {str(e)}"))
    else:
        messages.info(request, _("Esta acción solo está disponible para un solo presupuesto a la vez"))


@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'marca_modelo_vehiculo', 'fecha_creacion', 'fecha_vencimiento', 'estado', 'total']
    list_filter = ['estado', 'fecha_creacion', 'fecha_vencimiento']
    search_fields = ['cliente__nombre', 'vehiculo__chapa', 'vehiculo__marca', 'vehiculo__modelo']
    inlines = [PresupuestoServicioInline]
    readonly_fields = ['fecha_creacion', 'subtotal_servicios', 'total']

    actions = [generar_orden_trabajo]
    def marca_modelo_vehiculo(self, obj):
        return obj.marca_modelo_vehiculo
    marca_modelo_vehiculo.short_description = 'Vehículo'


