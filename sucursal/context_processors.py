from .models import Sucursal


def sucursal_activa(request):
    context = {
        'sucursales': Sucursal.objects.filter(activo=True),
        'sucursal_activa': None,
    }
    sucursal_id = None
    if hasattr(request, 'user') and request.user.is_authenticated:
        perfil = getattr(request.user, 'perfil', None)
        if perfil and perfil.sucursal_activa_id:
            context['sucursal_activa'] = perfil.sucursal_activa
        elif perfil:
            primera = perfil.sucursales_permitidas.filter(activo=True).first()
            if primera:
                context['sucursal_activa'] = primera
                perfil.sucursal_activa = primera
                perfil.save(update_fields=['sucursal_activa'])
    return context
