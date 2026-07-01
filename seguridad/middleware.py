from django.utils import timezone
from django.contrib.auth import logout
from django.contrib import messages
from datetime import datetime, timedelta
from django.shortcuts import redirect
from .utils import obtener_configuracion 

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.user.is_authenticated:
            # Tiempo dinámico (configuración del sistema)
            timeout_minutes = int(obtener_configuracion('tiempo_expiracion_sesion', 480))

            last_activity_str = request.session.get('last_activity')
            now = timezone.now()

            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    if timezone.is_naive(last_activity):
                        last_activity = timezone.make_aware(last_activity, timezone.get_current_timezone())
                    
                    timeout_duration = timedelta(minutes=timeout_minutes)
                    expires_at = last_activity + timeout_duration

                    if now >= expires_at:
                        # Sesión expirada
                        logout(request)
                        request.session.flush()
                        # Puedes mostrar un mensaje al front para abrir el modal
                        messages.error(request, 'Tu sesión ha expirado.', extra_tags='session_expired')
                        return redirect('/login?session_expired=1')
                except Exception:
                    # Si falla el parseo, reinicia last_activity
                    request.session['last_activity'] = now.isoformat()
            else:
                # Primera vez que se guarda last_activity
                request.session['last_activity'] = now.isoformat()

            # Si la sesión aún es válida, actualizar la actividad
            if request.user.is_authenticated:
                request.session['last_activity'] = now.isoformat()
        
        return self.get_response(request)
