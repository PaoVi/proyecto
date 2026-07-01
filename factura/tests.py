"""
Pruebas del módulo de facturación.
"""

# pylint: disable=no-member

from django.test import TestCase

from factura.models import Factura


class FacturaTest(TestCase):
    """Pruebas básicas del modelo Factura."""

    def test_creacion_factura(self):
        """Verifica que se pueda crear una factura."""

        factura = Factura.objects.create(
            establecimiento="001",
            punto_emision="001",
            numero=1,
            iva=10,
        )

        self.assertEqual(factura.numero, 1)
