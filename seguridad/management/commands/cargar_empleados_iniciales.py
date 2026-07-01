from django.core.management.base import BaseCommand
from empleado.models import Empleado
from datetime import date
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Carga empleados iniciales para el taller Iam Car'

    def handle(self, *args, **options):
        empleados = [
            # ==================== MECÁNICOS ====================
            {
                'nombre': 'Carlos Daniel Martínez',
                'cedula_ruc': '3456789',
                'fecha_nacimiento': date(1985, 8, 15),
                'telefono': '+595981234567',
                'direccion': 'Av. España 456, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'carlos.martinez@gmail.com',
                'fecha_ingreso': date(2020, 3, 10),
                'cargo': 'Mecánico Jefe',
                'salario_base': Decimal('4500000.00'),
                'estado': True
            },
            {
                'nombre': 'Roberto José González',
                'cedula_ruc': '4567890',
                'fecha_nacimiento': date(1990, 5, 22),
                'telefono': '+595982345678',
                'direccion': 'Calle Palma 789, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'roberto.gonzalez@gmail.com',
                'fecha_ingreso': date(2021, 6, 15),
                'cargo': 'Mecánico Especialista',
                'salario_base': Decimal('3800000.00'),
                'estado': True
            },
            {
                'nombre': 'Miguel Ángel Rojas',
                'cedula_ruc': '5678901',
                'fecha_nacimiento': date(1992, 11, 30),
                'telefono': '+595983456789',
                'direccion': 'Av. Brasilia 123, Lambaré',
                'ciudad': 'Lambaré',
                'correo_electronico': 'miguel.rojas@gmail.com',
                'fecha_ingreso': date(2022, 2, 20),
                'cargo': 'Mecánico General',
                'salario_base': Decimal('3200000.00'),
                'estado': True
            },
            {
                'nombre': 'Jorge Luis Benítez',
                'cedula_ruc': '6789012',
                'fecha_nacimiento': date(1988, 7, 8),
                'telefono': '+595984567890',
                'direccion': 'Calle Estrella 654, San Lorenzo',
                'ciudad': 'San Lorenzo',
                'correo_electronico': 'jorge.benitez@hotmail.com',
                'fecha_ingreso': date(2019, 11, 5),
                'cargo': 'Mecánico Electricista',
                'salario_base': Decimal('3500000.00'),
                'estado': True
            },

            # ==================== ELECTRICISTAS ====================
            {
                'nombre': 'Luis Alberto Fernández',
                'cedula_ruc': '7890123',
                'fecha_nacimiento': date(1987, 12, 25),
                'telefono': '+595985678901',
                'direccion': 'Av. Mariscal López 321, Fernando de la Mora',
                'ciudad': 'Fernando de la Mora',
                'correo_electronico': 'luis.fernandez@gmail.com',
                'fecha_ingreso': date(2020, 8, 12),
                'cargo': 'Electricista Automotriz',
                'salario_base': Decimal('3600000.00'),
                'estado': True
            },
            {
                'nombre': 'Diego Armando Silva',
                'cedula_ruc': '8901234',
                'fecha_nacimiento': date(1991, 9, 18),
                'telefono': '+595986789012',
                'direccion': 'Av. República Argentina 987, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'diego.silva@gmail.com',
                'fecha_ingreso': date(2021, 4, 5),
                'cargo': 'Especialista en Sistemas Eléctricos',
                'salario_base': Decimal('3400000.00'),
                'estado': True
            },

            # ==================== ADMINISTRATIVOS ====================
            {
                'nombre': 'Ana María García',
                'cedula_ruc': '9012345',
                'fecha_nacimiento': date(1983, 4, 5),
                'telefono': '+595987890123',
                'direccion': 'Calle San José 147, Capiatá',
                'ciudad': 'Capiatá',
                'correo_electronico': 'ana.garcia@gmail.com',
                'fecha_ingreso': date(2018, 1, 15),
                'cargo': 'Gerente Administrativa',
                'salario_base': Decimal('5200000.00'),
                'estado': True
            },
            {
                'nombre': 'María Elena Vargas',
                'cedula_ruc': '1122334',
                'fecha_nacimiento': date(1990, 6, 12),
                'telefono': '+595988901234',
                'direccion': 'Av. Aviadores del Chaco 258, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'maria.vargas@gmail.com',
                'fecha_ingreso': date(2020, 9, 1),
                'cargo': 'Recepcionista',
                'salario_base': Decimal('2800000.00'),
                'estado': True
            },
            {
                'nombre': 'Sofía Elizabeth Romero',
                'cedula_ruc': '2233445',
                'fecha_nacimiento': date(1988, 2, 28),
                'telefono': '+595989012345',
                'direccion': 'Calle Ytororó 369, Ñemby',
                'ciudad': 'Ñemby',
                'correo_electronico': 'sofia.romero@hotmail.com',
                'fecha_ingreso': date(2021, 3, 10),
                'cargo': 'Asistente Administrativa',
                'salario_base': Decimal('2500000.00'),
                'estado': True
            },

            # ==================== VENTAS Y ATENCIÓN AL CLIENTE ====================
            {
                'nombre': 'Juan Carlos Pereira',
                'cedula_ruc': '3344556',
                'fecha_nacimiento': date(1985, 10, 3),
                'telefono': '+595981112233',
                'direccion': 'Av. Artigas 753, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'juan.pereira@gmail.com',
                'fecha_ingreso': date(2019, 5, 20),
                'cargo': 'Asesor de Ventas',
                'salario_base': Decimal('3000000.00'),
                'estado': True
            },
            {
                'nombre': 'Patricia Lucía Acosta',
                'cedula_ruc': '4455667',
                'fecha_nacimiento': date(1993, 3, 17),
                'telefono': '+595982223344',
                'direccion': 'Calle Eligio Ayala 456, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'patricia.acosta@gmail.com',
                'fecha_ingreso': date(2022, 7, 8),
                'cargo': 'Atención al Cliente',
                'salario_base': Decimal('2400000.00'),
                'estado': True
            },

            # ==================== ESPECIALISTAS ====================
            {
                'nombre': 'Ricardo Antonio López',
                'cedula_ruc': '5566778',
                'fecha_nacimiento': date(1978, 11, 15),
                'telefono': '+595983334455',
                'direccion': 'Av. España 852, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'ricardo.lopez@gmail.com',
                'fecha_ingreso': date(2017, 8, 25),
                'cargo': 'Especialista en Transmisiones',
                'salario_base': Decimal('4800000.00'),
                'estado': True
            },
            {
                'nombre': 'Fernando David Morales',
                'cedula_ruc': '6677889',
                'fecha_nacimiento': date(1980, 1, 20),
                'telefono': '+595984445566',
                'direccion': 'Calle Manuel Domínguez 159, Luque',
                'ciudad': 'Luque',
                'correo_electronico': 'fernando.morales@gmail.com',
                'fecha_ingreso': date(2018, 12, 10),
                'cargo': 'Especialista en Frenos',
                'salario_base': Decimal('4200000.00'),
                'estado': True
            },

            # ==================== APRENDICES Y AYUDANTES ====================
            {
                'nombre': 'José Miguel Torres',
                'cedula_ruc': '7788990',
                'fecha_nacimiento': date(1998, 8, 30),
                'telefono': '+595985556677',
                'direccion': 'Av. Carlos Antonio López 753, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'jose.torres@gmail.com',
                'fecha_ingreso': date(2023, 1, 15),
                'cargo': 'Aprendiz de Mecánica',
                'salario_base': Decimal('1800000.00'),
                'estado': True
            },
            {
                'nombre': 'Andrea Beatriz Ruiz',
                'cedula_ruc': '8899001',
                'fecha_nacimiento': date(1997, 5, 14),
                'telefono': '+595986667788',
                'direccion': 'Calle Cerro Corá 246, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'andrea.ruiz@gmail.com',
                'fecha_ingreso': date(2023, 3, 1),
                'cargo': 'Ayudante de Taller',
                'salario_base': Decimal('1600000.00'),
                'estado': True
            },

            # ==================== EMPLEADOS INACTIVOS ====================
            {
                'nombre': 'Roberto Carlos Díaz',
                'cedula_ruc': '9900112',
                'fecha_nacimiento': date(1975, 12, 8),
                'telefono': '+595987778899',
                'direccion': 'Av. Fernando de la Mora 357, Fernando de la Mora',
                'ciudad': 'Fernando de la Mora',
                'correo_electronico': 'roberto.diaz@hotmail.com',
                'fecha_ingreso': date(2015, 6, 20),
                'cargo': 'Mecánico General',
                'salario_base': Decimal('3500000.00'),
                'estado': False
            },
            {
                'nombre': 'Laura Patricia Castro',
                'cedula_ruc': '1011121',
                'fecha_nacimiento': date(1982, 7, 22),
                'telefono': '+595988889900',
                'direccion': 'Calle San Roque González 468, Asunción',
                'ciudad': 'Asunción',
                'correo_electronico': 'laura.castro@gmail.com',
                'fecha_ingreso': date(2016, 4, 10),
                'cargo': 'Asistente Administrativa',
                'salario_base': Decimal('2200000.00'),
                'estado': False
            }
        ]

        created_count = 0
        updated_count = 0
        errores = []

        for empleado_data in empleados:
            # Buscar por cédula/RUC (único)
            cedula_ruc = empleado_data['cedula_ruc']
            try:
                empleado = Empleado.objects.get(cedula_ruc=cedula_ruc)
                # Actualizar empleado existente
                for key, value in empleado_data.items():
                    setattr(empleado, key, value)
                
                empleado.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⮐ {empleado_data["nombre"]} - {cedula_ruc} (actualizado)'))
            except Empleado.DoesNotExist:
                try:
                    # Crear nuevo empleado
                    Empleado.objects.create(**empleado_data)
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ {empleado_data["nombre"]} - {cedula_ruc}'))
                except Exception as e:
                    errores.append(f"Error con {empleado_data['nombre']} - {cedula_ruc}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f'✗ {empleado_data["nombre"]} - {cedula_ruc}: {str(e)}'))
            except Exception as e:
                errores.append(f"Error con {empleado_data['nombre']} - {cedula_ruc}: {str(e)}")
                self.stdout.write(self.style.ERROR(f'✗ {empleado_data["nombre"]} - {cedula_ruc}: {str(e)}'))

        # Estadísticas de emails
        gmail_count = Empleado.objects.filter(correo_electronico__endswith='@gmail.com').count()
        hotmail_count = Empleado.objects.filter(correo_electronico__endswith='@hotmail.com').count()
        total_emails = gmail_count + hotmail_count
        
        if total_emails > 0:
            gmail_percentage = (gmail_count / total_emails) * 100
            hotmail_percentage = (hotmail_count / total_emails) * 100
        else:
            gmail_percentage = hotmail_percentage = 0

        # Estadísticas generales
        total_empleados = Empleado.objects.count()
        activos = Empleado.objects.filter(estado=True).count()
        inactivos = Empleado.objects.filter(estado=False).count()

        # Agrupar por cargo
        cargos = {}
        for empleado in Empleado.objects.all():
            cargo = empleado.cargo
            if cargo in cargos:
                cargos[cargo] += 1
            else:
                cargos[cargo] = 1

        self.stdout.write(self.style.SUCCESS(
            f'\nProceso completado: {created_count} empleados creados, {updated_count} empleados actualizados'
        ))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\nErrores encontrados ({len(errores)}):'))
            for error in errores:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Todos los empleados se procesaron sin errores'))

        self.stdout.write(self.style.SUCCESS(
            f'Total en sistema: {total_empleados} empleados ({activos} activos, {inactivos} inactivos)'
        ))
        
        self.stdout.write(self.style.SUCCESS('\nDistribución de emails:'))
        self.stdout.write(self.style.SUCCESS(f'  - Gmail: {gmail_count} ({gmail_percentage:.1f}%)'))
        self.stdout.write(self.style.SUCCESS(f'  - Hotmail: {hotmail_count} ({hotmail_percentage:.1f}%)'))
        
        self.stdout.write(self.style.SUCCESS('\nDistribución por cargo:'))
        for cargo, cantidad in sorted(cargos.items()):
            self.stdout.write(self.style.SUCCESS(f'  - {cargo}: {cantidad}'))
        
        self.stdout.write(self.style.SUCCESS('Empleados cargados exitosamente!'))