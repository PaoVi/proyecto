from django.db import migrations
from django.db import migrations


def backfill_sucursal(apps, schema_editor):
    Sucursal = apps.get_model('sucursal', 'Sucursal')
    sucursal_matriz, _ = Sucursal.objects.get_or_create(
        nombre="Matriz",
        defaults={
            "direccion": "Dirección principal",
            "telefono": "",
            "establecimiento": "001",
            "punto_emision": "001",
            "activo": True,
        }
    )
    sid = sucursal_matriz.pk

    models_to_backfill = [
        ('compra', 'Compra'),
        ('compra', 'BitacoraCompra'),
        ('empleado', 'Empleado'),
        ('factura', 'Factura'),
        ('factura', 'NotaCredito'),
        ('finanza', 'Caja'),
        ('finanza', 'Cobro'),
        ('finanza', 'CuentaCobrar'),
        ('finanza', 'CuentaPagar'),
        ('finanza', 'MovimientoFinanciero'),
        ('finanza', 'PagoProveedor'),
        ('insumo', 'Insumo'),
        ('insumo', 'MovimientoStock'),
        ('insumo', 'SubInsumo'),
        ('notificacion', 'LogEnvio'),
        ('orden_trabajo', 'OrdenTrabajo'),
        ('orden_trabajo', 'BitacoraOrden'),
        ('presupuesto', 'Presupuesto'),
        ('presupuesto', 'BitacoraPresupuesto'),
        ('seguridad', 'ConfiguracionSistema'),
    ]

    for app_label, model_name in models_to_backfill:
        Model = apps.get_model(app_label, model_name)
        updated = Model.objects.filter(sucursal__isnull=True).update(sucursal_id=sid)
        if updated:
            print(f"  {app_label}.{model_name}: {updated} registros actualizados")

    Perfil = apps.get_model('seguridad', 'PerfilUsuario')
    updated = Perfil.objects.filter(sucursal_activa__isnull=True).update(sucursal_activa_id=sid)
    if updated:
        print(f"  seguridad.PerfilUsuario (sucursal_activa): {updated} perfiles actualizados")


class Migration(migrations.Migration):

    dependencies = [
        ('compra', '0012_bitacoracompra_sucursal_compra_sucursal'),
        ('empleado', '0011_empleado_sucursal'),
        ('factura', '0017_factura_sucursal_notacredito_sucursal'),
        ('finanza', '0004_caja_sucursal_cobro_sucursal_cuentacobrar_sucursal_and_more'),
        ('insumo', '0016_insumo_sucursal_movimientostock_sucursal_and_more'),
        ('notificacion', '0003_logenvio_sucursal'),
        ('orden_trabajo', '0025_bitacoraorden_sucursal_ordentrabajo_sucursal'),
        ('presupuesto', '0022_bitacorapresupuesto_sucursal_presupuesto_sucursal'),
        ('seguridad', '0013_configuracionsistema_sucursal_and_more'),
        ('sucursal', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_sucursal, migrations.RunPython.noop),
    ]
