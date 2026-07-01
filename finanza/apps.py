# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=unused-import

from django.apps import AppConfig


class FinanzaConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "finanza"

    verbose_name = "Finanzas"

    def ready(self):
        import finanza.signals
