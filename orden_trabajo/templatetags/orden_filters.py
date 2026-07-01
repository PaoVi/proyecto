from django import template

register = template.Library()

@register.filter
def minutos_to_hhmm(minutos):
    """Convierte minutos a formato HH:MM"""
    if not minutos:
        return "00:00"
    try:
        minutos = int(minutos)
        horas = minutos // 60
        mins = minutos % 60
        return f"{horas:02d}:{mins:02d}"
    except (ValueError, TypeError):
        return "00:00"