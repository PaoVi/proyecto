from django.apps import AppConfig

class SeguridadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seguridad'
    
    def ready(self):
        print("App Seguridad está lista!")
        import seguridad.signals