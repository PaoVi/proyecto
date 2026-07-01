from django import template

register = template.Library()

@register.filter
def type_name(value):
    """Devuelve el nombre del tipo de dato"""
    return type(value).__name__

get_type = type_name
