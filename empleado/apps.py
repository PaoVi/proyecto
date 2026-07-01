from django.apps import AppConfig


class EmpleadoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'empleado'

    def ready(self):
        print("App Empleado está lista!")
        from . import signals 
