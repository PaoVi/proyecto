from django.apps import AppConfig

class ClienteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cliente'

    def ready(self):
        print("App Cliente está lista!")
