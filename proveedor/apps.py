from django.apps import AppConfig

class ProveedorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "proveedor"

    def ready(self):
        print("App Proveedor está lista!")
