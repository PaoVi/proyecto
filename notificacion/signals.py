from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

from .emails import enviar_bienvenida

Cliente = apps.get_model("cliente", "Cliente")

@receiver(post_save, sender=Cliente, dispatch_uid="notificacion_cliente_bienvenida")
def cliente_creado_envio_bienvenida(sender, instance, created, **kwargs):
    if created and instance.email:
        enviar_bienvenida(
            destinatario=instance.email,
            nombre=instance.nombre,
            cliente_id=instance.pk
        )
