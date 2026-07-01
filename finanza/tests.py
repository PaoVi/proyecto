from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from cliente.models import Cliente
from proveedor.models import Proveedor
from factura.models import Factura
from compra.models import Compra

from .models import (
    Caja,
    MovimientoFinanciero,
    CuentaCobrar,
    CuentaPagar,
    Cobro,
    PagoProveedor,
)


class CajaModelTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            rol="Administrador",
        )
        self.caja = Caja.objects.create(
            monto_inicial=Decimal("1000.00"),
            saldo_actual=Decimal("1000.00"),
            usuario_apertura=self.user,
        )

    def test_caja_apertura_ok(self):
        self.assertEqual(self.caja.estado, "abierta")
        self.assertEqual(self.caja.saldo_actual, Decimal("1000.00"))

    def test_caja_cierre_actualiza_saldos(self):
        self.caja.total_ingresos_cierre = self.caja.total_ingresos
        self.caja.total_egresos_cierre = self.caja.total_egresos
        self.caja.saldo_cierre = self.caja.saldo_actual
        self.caja.estado = "cerrada"
        self.caja.save()

        self.assertEqual(self.caja.estado, "cerrada")


class MovimientoFinancieroModelTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser2",
            password="testpass123",
            rol="Administrador",
        )
        self.caja = Caja.objects.create(
            monto_inicial=Decimal("5000.00"),
            saldo_actual=Decimal("5000.00"),
            usuario_apertura=self.user,
        )

    def test_crear_ingreso_actualiza_saldo(self):
        MovimientoFinanciero.objects.create(
            caja=self.caja,
            tipo="ingreso",
            origen="manual",
            descripcion="Test ingreso",
            monto=Decimal("500.00"),
            usuario=self.user,
        )
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal("5500.00"))

    def test_crear_egreso_actualiza_saldo(self):
        MovimientoFinanciero.objects.create(
            caja=self.caja,
            tipo="egreso",
            origen="manual",
            descripcion="Test egreso",
            monto=Decimal("300.00"),
            usuario=self.user,
        )
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.saldo_actual, Decimal("4700.00"))


class CuentaCobrarModelTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser3",
            password="testpass123",
            rol="Administrador",
        )
        self.cliente = Cliente.objects.create(
            tipo_cliente="fisica",
            tipo_documento="CI_PY",
            numero_documento="1234567",
            nombre="Cliente Test",
            telefono="+595981234567",
            email="cliente@test.com",
        )

    def _crear_factura(self, total):
        return Factura.objects.create(
            cliente=self.cliente,
            cliente_nombre=self.cliente.nombre,
            cliente_ruc=self.cliente.numero_documento,
            cliente_direccion="Direccion Test",
            condicion_venta="contado",
            subtotal=total,
            total_general=total,
            estado="ACTIVA",
        )

    def test_saldo_pendiente_se_calcula_auto(self):
        factura = self._crear_factura(Decimal("1000.00"))
        cuenta = CuentaCobrar(
            factura=factura,
            cliente=self.cliente,
            monto_total=Decimal("1000.00"),
            monto_pagado=Decimal("300.00"),
            fecha_vencimiento="2025-12-31",
        )
        cuenta.save()
        self.assertEqual(cuenta.saldo_pendiente, Decimal("700.00"))
        self.assertFalse(cuenta.pagado)

    def test_cuenta_marcada_pagada_al_completar(self):
        factura = self._crear_factura(Decimal("500.00"))
        cuenta = CuentaCobrar(
            factura=factura,
            cliente=self.cliente,
            monto_total=Decimal("500.00"),
            monto_pagado=Decimal("500.00"),
            fecha_vencimiento="2025-12-31",
        )
        cuenta.save()
        self.assertEqual(cuenta.saldo_pendiente, Decimal("0.00"))
        self.assertTrue(cuenta.pagado)


class CuentaPagarModelTest(TestCase):

    def setUp(self):
        self.proveedor = Proveedor.objects.create(
            ruc="80012345-1",
            razon_social="Proveedor Test",
            telefono="+595981234567",
        )

    def _crear_compra(self, total):
        return Compra.objects.create(
            proveedor=self.proveedor,
            total=total,
        )

    def test_saldo_pendiente_se_calcula_auto(self):
        compra = self._crear_compra(Decimal("2000.00"))
        cuenta = CuentaPagar(
            compra=compra,
            proveedor=self.proveedor,
            monto_total=Decimal("2000.00"),
            monto_pagado=Decimal("500.00"),
            fecha_vencimiento="2025-12-31",
        )
        cuenta.save()
        self.assertEqual(cuenta.saldo_pendiente, Decimal("1500.00"))
        self.assertFalse(cuenta.pagado)

    def test_cuenta_marcada_pagada_al_completar(self):
        compra = self._crear_compra(Decimal("1000.00"))
        cuenta = CuentaPagar(
            compra=compra,
            proveedor=self.proveedor,
            monto_total=Decimal("1000.00"),
            monto_pagado=Decimal("1000.00"),
            fecha_vencimiento="2025-12-31",
        )
        cuenta.save()
        self.assertEqual(cuenta.saldo_pendiente, Decimal("0.00"))
        self.assertTrue(cuenta.pagado)


class CobroModelTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser4",
            password="testpass123",
            rol="Administrador",
        )
        self.cliente = Cliente.objects.create(
            tipo_cliente="fisica",
            tipo_documento="CI_PY",
            numero_documento="7654321",
            nombre="Cliente Cobro",
            telefono="+595981234567",
            email="cobro@test.com",
        )
        factura = Factura.objects.create(
            cliente=self.cliente,
            cliente_nombre=self.cliente.nombre,
            cliente_ruc=self.cliente.numero_documento,
            condicion_venta="contado",
            subtotal=Decimal("1000.00"),
            total_general=Decimal("1000.00"),
            estado="ACTIVA",
        )
        self.cuenta = CuentaCobrar.objects.create(
            factura=factura,
            cliente=self.cliente,
            monto_total=Decimal("1000.00"),
            fecha_vencimiento="2025-12-31",
        )

    def test_cobro_actualiza_monto_pagado(self):
        Cobro.objects.create(
            cuenta=self.cuenta,
            monto=Decimal("400.00"),
            usuario=self.user,
        )
        self.cuenta.refresh_from_db()
        self.assertEqual(self.cuenta.monto_pagado, Decimal("400.00"))
        self.assertEqual(self.cuenta.saldo_pendiente, Decimal("600.00"))
        self.assertFalse(self.cuenta.pagado)

    def test_cobro_completa_cuenta(self):
        Cobro.objects.create(
            cuenta=self.cuenta,
            monto=Decimal("1000.00"),
            usuario=self.user,
        )
        self.cuenta.refresh_from_db()
        self.assertEqual(self.cuenta.monto_pagado, Decimal("1000.00"))
        self.assertEqual(self.cuenta.saldo_pendiente, Decimal("0.00"))
        self.assertTrue(self.cuenta.pagado)
