from django import template

register = template.Library()

@register.filter
def minutos_a_hhmm(minutos):
    """
    Convierte minutos a formato HH:MM
    Uso: {{ 125|minutos_a_hhmm }} -> "02:05"
    """
    if minutos is None:
        return "00:00"
    
    try:
        minutos = int(float(minutos))
        horas = minutos // 60
        mins = minutos % 60
        return f"{horas:02d}:{mins:02d}"
    except (ValueError, TypeError):
        return "00:00"
    

@register.filter
def get_item(queryset, empleado):
    """
    Filtro para obtener la asignación de un empleado específico en el queryset.
    Uso: {{ orden.asignaciones.all|get_item:empleado }}
    """
    if not queryset:
        return None
    for asignacion in queryset:
        if asignacion.empleado.id_empleado == empleado.id_empleado:
            return asignacion
    return None