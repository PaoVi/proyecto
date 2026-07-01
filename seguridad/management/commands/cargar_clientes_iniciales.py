from django.core.management.base import BaseCommand
from cliente.models import Cliente
from datetime import date

class Command(BaseCommand):
    help = 'Carga clientes iniciales para el taller Iam Car'

    def handle(self, *args, **options):
        clientes = [
            # ==================== PERSONAS FÍSICAS ====================
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '1234567',
                'nombre': 'Juan Carlos Pereira',
                'telefono': '+595981123456',
                'email': 'juan.pereira@gmail.com',
                'direccion': 'Av. España 123, Asunción',
                'fecha_nacimiento': date(1985, 5, 15),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '2345678',
                'nombre': 'María Elena González',
                'telefono': '+595982234567',
                'email': 'maria.gonzalez@hotmail.com',
                'direccion': 'Calle Palma 456, Asunción',
                'fecha_nacimiento': date(1990, 8, 22),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '3456789',
                'nombre': 'Roberto Daniel Martínez',
                'telefono': '+595983345678',
                'email': 'roberto.martinez@yahoo.com',
                'direccion': 'Av. Brasilia 789, Lambaré',
                'fecha_nacimiento': date(1978, 3, 10),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '4567890',
                'nombre': 'Ana Lucía Benítez',
                'telefono': '+595984456789',
                'email': 'ana.benitez@gmail.com',
                'direccion': 'Calle Estrella 321, San Lorenzo',
                'fecha_nacimiento': date(1988, 11, 30),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '5678901',
                'nombre': 'Carlos Alberto Fernández',
                'telefono': '+595985567890',
                'email': 'carlos.fernandez@outlook.com',
                'direccion': 'Av. Mariscal López 654, Fernando de la Mora',
                'fecha_nacimiento': date(1992, 7, 8),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '6789012',
                'nombre': 'Sofía Alejandra Rojas',
                'telefono': '+595986678901',
                'email': 'sofia.rojas@gmail.com',
                'direccion': 'Calle Manuel Domínguez 987, Luque',
                'fecha_nacimiento': date(1983, 12, 25),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '7890123',
                'nombre': 'Miguel Ángel Silva',
                'telefono': '+595987789012',
                'email': 'miguel.silva@hotmail.com',
                'direccion': 'Av. República Argentina 147, Asunción',
                'fecha_nacimiento': date(1975, 9, 18),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '8901234',
                'nombre': 'Patricia Elizabeth Vargas',
                'telefono': '+595988890123',
                'email': 'patricia.vargas@gmail.com',
                'direccion': 'Calle San José 258, Capiatá',
                'fecha_nacimiento': date(1995, 4, 5),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '9012345',
                'nombre': 'Diego Armando Romero',
                'telefono': '+595989901234',
                'email': 'diego.romero@yahoo.com',
                'direccion': 'Av. Aviadores del Chaco 753, Asunción',
                'fecha_nacimiento': date(1980, 6, 12),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '1122334',
                'nombre': 'Laura Beatriz Acosta',
                'telefono': '+595981122334',
                'email': 'laura.acosta@gmail.com',
                'direccion': 'Calle Ytororó 369, Ñemby',
                'fecha_nacimiento': date(1987, 2, 28),
                'is_active': True
            },

            # ==================== PERSONAS JURÍDICAS ====================
            {
                'tipo_cliente': 'juridica',
                'tipo_documento': 'RUC',
                'numero_documento': '80012345-1',
                'nombre': 'Distribuidora Comercial S.A.',
                'telefono': '+59521234567',
                'email': 'ventas@distribuidoracomercial.com.py',
                'direccion': 'Av. Artigas 1234, Asunción',
                'fecha_constitucion': date(2010, 3, 15),
                'is_active': True
            },
            {
                'tipo_cliente': 'juridica',
                'tipo_documento': 'RUC',
                'numero_documento': '80023456-2',
                'nombre': 'Importadora del Paraguay S.R.L.',
                'telefono': '+59521245678',
                'email': 'contacto@importadorapy.com.py',
                'direccion': 'Calle Eligio Ayala 567, Asunción',
                'fecha_constitucion': date(2015, 7, 20),
                'is_active': True
            },
            {
                'tipo_cliente': 'juridica',
                'tipo_documento': 'RUC',
                'numero_documento': '80034567-3',
                'nombre': 'Constructora Moderna S.A.',
                'telefono': '+59521256789',
                'email': 'info@constructoramoderna.com.py',
                'direccion': 'Av. España 890, Asunción',
                'fecha_constitucion': date(2008, 11, 5),
                'is_active': True
            },
            {
                'tipo_cliente': 'juridica',
                'tipo_documento': 'RUC',
                'numero_documento': '80045678-4',
                'nombre': 'Agropecuaria Productiva S.R.L.',
                'telefono': '+59521267890',
                'email': 'administracion@agroproductiva.com.py',
                'direccion': 'Ruta 2 Km 12, San Lorenzo',
                'fecha_constitucion': date(2012, 5, 30),
                'is_active': True
            },
            {
                'tipo_cliente': 'juridica',
                'tipo_documento': 'RUC',
                'numero_documento': '80056789-5',
                'nombre': 'Transporte Rápido S.A.',
                'telefono': '+59521278901',
                'email': 'logistica@transportepy.com.py',
                'direccion': 'Av. Fernando de la Mora 234, Fernando de la Mora',
                'fecha_constitucion': date(2018, 9, 10),
                'is_active': True
            },
            {
                'tipo_cliente': 'juridica',
                'tipo_documento': 'RUC',
                'numero_documento': '80067890-6',
                'nombre': 'Inversiones Capital S.A.',
                'telefono': '+59521289012',
                'email': 'inversiones@capital.com.py',
                'direccion': 'Edificio Centro, Piso 5, Oficina 502, Asunción',
                'fecha_constitucion': date(2005, 1, 25),
                'is_active': True
            },

            # ==================== CLIENTES CON PASAPORTE ====================
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'PAS',
                'numero_documento': 'AB123456',
                'nombre': 'John Michael Smith',
                'telefono': '+595981234567',
                'email': 'john.smith@email.com',
                'direccion': 'Hotel Guarani, Asunción',
                'fecha_nacimiento': date(1972, 4, 18),
                'is_active': True
            },
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'PAS',
                'numero_documento': 'CD789012',
                'nombre': 'Maria Silva Santos',
                'telefono': '+595982345678',
                'email': 'maria.santos@email.com',
                'direccion': 'Av. Santa Teresa, Ciudad del Este',
                'fecha_nacimiento': date(1985, 8, 12),
                'is_active': True
            },

            # ==================== CLIENTES INACTIVOS ====================
            {
                'tipo_cliente': 'fisica',
                'tipo_documento': 'CI_PY',
                'numero_documento': '9988776',
                'nombre': 'Luis Alberto Mora',
                'telefono': '+595981998877',
                'email': 'luis.mora@email.com',
                'direccion': 'Calle Cerro Corá 654, Asunción',
                'fecha_nacimiento': date(1965, 10, 3),
                'is_active': False
            },
            {
                'tipo_cliente': 'juridica',
                'tipo_documento': 'RUC',
                'numero_documento': '80098765-7',
                'nombre': 'Empresa Cerrada S.A.',
                'telefono': '+59521345678',
                'email': 'info@empresacerrada.com.py',
                'direccion': 'Av. Carlos Antonio López 321, Asunción',
                'fecha_constitucion': date(2000, 12, 15),
                'is_active': False
            }
        ]

        created_count = 0
        updated_count = 0
        errores = []

        for cliente_data in clientes:
            # Buscar por número de documento (único)
            numero_documento = cliente_data['numero_documento']
            try:
                cliente = Cliente.objects.get(numero_documento=numero_documento)
                # Actualizar cliente existente
                for key, value in cliente_data.items():
                    setattr(cliente, key, value)
                
                cliente.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⮐ {cliente_data["nombre"]} - {numero_documento} (actualizado)'))
            except Cliente.DoesNotExist:
                try:
                    # Crear nuevo cliente
                    Cliente.objects.create(**cliente_data)
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ {cliente_data["nombre"]} - {numero_documento}'))
                except Exception as e:
                    errores.append(f"Error con {cliente_data['nombre']} - {numero_documento}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f'✗ {cliente_data["nombre"]} - {numero_documento}: {str(e)}'))
            except Exception as e:
                errores.append(f"Error con {cliente_data['nombre']} - {numero_documento}: {str(e)}")
                self.stdout.write(self.style.ERROR(f'✗ {cliente_data['nombre']} - {numero_documento}: {str(e)}'))

        # Estadísticas
        total_clientes = Cliente.objects.count()
        activos = Cliente.objects.filter(is_active=True).count()
        fisicos = Cliente.objects.filter(tipo_cliente='fisica').count()
        juridicos = Cliente.objects.filter(tipo_cliente='juridica').count()

        self.stdout.write(self.style.SUCCESS(
            f'\nProceso completado: {created_count} clientes creados, {updated_count} clientes actualizados'
        ))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\nErrores encontrados ({len(errores)}):'))
            for error in errores:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Todos los clientes se procesaron sin errores'))

        self.stdout.write(self.style.SUCCESS(
            f'Total en sistema: {total_clientes} clientes ({activos} activos)'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Desglose: {fisicos} personas físicas, {juridicos} personas jurídicas'
        ))
        self.stdout.write(self.style.SUCCESS('Clientes cargados exitosamente!'))