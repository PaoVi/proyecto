from django.apps import AppConfig


class OrdenTrabajoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orden_trabajo'

    def ready(self):
        print("App OrdenTrabajo está lista!")
