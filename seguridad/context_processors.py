# context_processors.py
from django.utils import timezone
from datetime import datetime, timedelta
from .utils import obtener_configuracion

def session_timeout(request):
    remaining_seconds = 0
    is_expired = False

    if request.user.is_authenticated:
        timeout_minutes = int(obtener_configuracion('tiempo_expiracion_sesion', 120))
        last_activity_str = request.session.get('last_activity')

        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                if timezone.is_naive(last_activity):
                    last_activity = timezone.make_aware(last_activity, timezone.get_current_timezone())

                expires_at = last_activity + timedelta(minutes=timeout_minutes)
                delta = expires_at - timezone.now()
                remaining_seconds = max(int(delta.total_seconds()), 0)
                is_expired = remaining_seconds == 0
            except Exception:
                remaining_seconds = 0
                is_expired = True

    return {
        "session_remaining_seconds": remaining_seconds,
        "session_is_expired": is_expired,
    }
