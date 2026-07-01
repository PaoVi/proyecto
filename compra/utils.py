"""
Utilidades para compras.
"""

from seguridad.models import ConfiguracionSistema


def get_config(clave, default=""):
    """Obtener configuración del sistema"""
    try:
        return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
    except ConfiguracionSistema.DoesNotExist:
        return default