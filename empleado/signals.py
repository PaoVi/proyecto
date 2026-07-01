from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Empleado

@receiver(post_save, sender=Empleado)
def sync_user_email_from_empleado(sender, instance: Empleado, **kwargs):
    """
    Si el empleado tiene un usuario vinculado, empuja su correo_electronico al email del usuario
    cuando sean distintos.
    """
    user = getattr(instance, "user", None)
    if not user:
        return
    emp_mail = (instance.correo_electronico or "").strip()
    usr_mail = (user.email or "").strip()
    if emp_mail and emp_mail != usr_mail:
        user.email = emp_mail
        # evitamos señales innecesarias si no hay cambios reales la próxima vez
        user.save(update_fields=["email"])
