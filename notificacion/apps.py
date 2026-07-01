from django.apps import AppConfig


class Notificacionfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notificacion'

    def ready(self):
        print("App Notificacion está lista!")
        from . import signals 
