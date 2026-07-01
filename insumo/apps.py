from django.apps import AppConfig


class insumoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'insumo'

    def ready(self):
        print("App Insumo está lista!")
