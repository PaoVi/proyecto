"""proyecto URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from seguridad import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('seguridad.urls')),
    path('', include('cliente.urls')),
    path('', include('empleado.urls')),
    path('', include('vehiculo.urls')),
    path('', include('proveedor.urls')),
    path('', include('insumo.urls')),
    path('', include('servicio.urls')),
    path('', include('presupuesto.urls')),
    path('', include('orden_trabajo.urls')),
    path('', include('factura.urls')),
    path('', include('compra.urls')),
    path('', include('finanza.urls')),
    path('', include('notificacion.urls')),
]


handler403 = views.custom_permission_denied  # Para error 403
handler404 = views.custom_page_not_found     # Para error 404  
handler500 = views.custom_server_error       # Para error 500