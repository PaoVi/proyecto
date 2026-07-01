from django.core.cache import cache
from .models import ConfiguracionSistema

def obtener_configuracion(clave, valor_por_defecto=None):
    """
    Obtiene una configuración del sistema, con caching para mejor performance
    SOLO si la configuración está ACTIVA
    """
    # Intentar obtener del cache primero
    config_cache = cache.get(f'config_{clave}')
    if config_cache is not None:
        return config_cache
    
    try:
        # Verificar que la configuración esté activa
        config = ConfiguracionSistema.objects.get(clave=clave, activo=True)
        valor = config.valor
        
        # Convertir según el tipo
        if config.tipo == 'integer':
            try:
                valor = int(valor)
            except (ValueError, TypeError):
                valor = valor_por_defecto
        elif config.tipo == 'boolean':
            valor = str(valor).lower() in ('true', '1', 'yes', 'si', 'verdadero')
        elif config.tipo == 'json':
            try:
                import json
                valor = json.loads(valor)
            except:
                valor = valor_por_defecto
        
        # Guardar en cache por 5 minutos
        cache.set(f'config_{clave}', valor, 300)
        return valor
        
    except ConfiguracionSistema.DoesNotExist:
        # Si no existe o está inactiva, devolver valor por defecto
        return valor_por_defecto