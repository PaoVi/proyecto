# presupuesto/migrations/0001_initial.py
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
from datetime import timedelta

def default_fecha_vencimiento():
    return (timezone.now() + timedelta(days=15)).date()

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cliente', '0009_alter_cliente_numero_documento'),
        ('vehiculo', '0006_alter_vehiculo_tipo_combustible_alter_vehiculo_uso'),
        ('servicio', '0007_alter_servicio_categoria'),
    ]

    operations = [
        migrations.CreateModel(
            name='Presupuesto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.TextField(blank=True, help_text='Descripción general del presupuesto', null=True, verbose_name='Descripción')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('fecha_vencimiento', models.DateField(default=default_fecha_vencimiento, verbose_name='Fecha de vencimiento')),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('aceptado', 'Aceptado'), ('rechazado', 'Rechazado'), ('vencido', 'Vencido')], default='pendiente', max_length=20, verbose_name='Estado')),
                ('descuento', models.DecimalField(decimal_places=2, default=0, help_text='Monto de descuento en guaraníes', max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Descuento')),
                ('iva_porcentaje', models.DecimalField(choices=[(10, '10% - Con IVA'), (0, '0% - Sin IVA')], decimal_places=2, default=10, help_text='Porcentaje de IVA aplicable', max_digits=5, verbose_name='IVA %')),
                ('iva_monto', models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Monto IVA')),
                ('subtotal_servicios', models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Subtotal servicios')),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Total')),
                ('cliente', models.ForeignKey(error_messages={'blank': 'Este campo es obligatorio', 'null': 'Este campo es obligatorio'}, on_delete=django.db.models.deletion.CASCADE, to='cliente.cliente', verbose_name='Cliente')),
                ('vehiculo', models.ForeignKey(error_messages={'blank': 'Este campo es obligatorio', 'null': 'Este campo es obligatorio'}, help_text='Seleccione un vehículo por chapa', on_delete=django.db.models.deletion.CASCADE, to='vehiculo.vehiculo', verbose_name='Vehículo')),
            ],
            options={
                'verbose_name': 'Presupuesto',
                'verbose_name_plural': 'Presupuestos',
                'ordering': ('-fecha_creacion',),
                'permissions': [('gestionar_presupuestos', 'Puede gestionar presupuestos'), ('ver_presupuestos', 'Puede ver presupuestos'), ('agregar_presupuestos', 'Puede registrar presupuestos'), ('editar_presupuestos', 'Puede actualizar presupuestos'), ('cambiar_estado_presupuestos', 'Puede cambiar estado de presupuestos')],
            },
        ),
        migrations.CreateModel(
            name='PresupuestoServicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=2, default=1, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='Cantidad')),
                ('presupuesto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='presupuesto.presupuesto')),
                ('servicio', models.ForeignKey(error_messages={'blank': 'Este campo es obligatorio', 'null': 'Este campo es obligatorio'}, on_delete=django.db.models.deletion.CASCADE, to='servicio.servicio')),
            ],
            options={
                'verbose_name': 'Servicio del presupuesto',
                'verbose_name_plural': 'Servicios del presupuesto',
                'unique_together': {('presupuesto', 'servicio')},
            },
        ),
    ]