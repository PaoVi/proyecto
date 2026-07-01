# pylint: disable=unused-import
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring

from django.apps import AppConfig


class CompraConfig(AppConfig):

    default_auto_field = (
        'django.db.models.BigAutoField'
    )

    name = 'compra'

    def ready(self):

        import compra.signals
