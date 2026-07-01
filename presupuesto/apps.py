from django.apps import AppConfig


class PresupuestoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'presupuesto'

    def ready(self):
        print("App Presupuesto está lista!")
