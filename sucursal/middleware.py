from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import Sucursal


class SucursalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        sucursal_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            perfil = getattr(request.user, 'perfil', None)
            if perfil and perfil.sucursal_activa_id:
                sucursal_id = perfil.sucursal_activa_id
            elif perfil:
                sucursal_id = getattr(settings, 'SUCURSAL_DEFAULT_ID', 1)

        if sucursal_id:
            try:
                request.sucursal = Sucursal.objects.get(pk=sucursal_id, activo=True)
            except Sucursal.DoesNotExist:
                request.sucursal = None
        else:
            request.sucursal = None

        return self.get_response(request)
