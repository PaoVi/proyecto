from django.core.management.base import BaseCommand
from cliente import models
from vehiculo.models import Vehiculo
from cliente.models import Cliente
from django.db import models
import random

class Command(BaseCommand):
    help = 'Carga vehículos iniciales de ejemplo para el taller Iam Car'

    def handle(self, *args, **options):
        # Obtener algunos clientes existentes para asignar como propietarios
        try:
            clientes = list(Cliente.objects.filter(is_active=True)[:10])
            if not clientes:
                self.stdout.write(self.style.WARNING('No hay clientes activos. Creando vehículos sin propietario.'))
                clientes = []
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error al obtener clientes: {e}'))
            clientes = []

        vehiculos = [
            # ==================== TOYOTA ====================
            {
                'marca': 'Toyota',
                'modelo': 'Hilux',
                'anio': 2022,
                'color': 'Blanco',
                'nro_chapa': 'ABC1234',
                'nro_chasis': 'JTFBK122300123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '2755',
                'tipo_combustible': 'Diésel',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': False,
                'estado': True
            },
            {
                'marca': 'Toyota',
                'modelo': 'Corolla',
                'anio': 2023,
                'color': 'Gris Plata',
                'nro_chapa': 'DEF5678',
                'nro_chasis': 'JTNKU123450123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1987',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },
            {
                'marca': 'Toyota',
                'modelo': 'Yaris',
                'anio': 2021,
                'color': 'Rojo',
                'nro_chapa': 'GHI9012',
                'nro_chasis': 'JTDKN123450123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1496',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'MANUAL',
                'alarma': False,
                'gps': False,
                'estado': True
            },

            # ==================== VOLKSWAGEN ====================
            {
                'marca': 'Volkswagen',
                'modelo': 'Gol Trend',
                'anio': 2020,
                'color': 'Negro',
                'nro_chapa': 'JKL3456',
                'nro_chasis': '9BWZZZ377ZT004321',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1598',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'MANUAL',
                'alarma': True,
                'gps': False,
                'estado': True
            },
            {
                'marca': 'Volkswagen',
                'modelo': 'Amarok',
                'anio': 2022,
                'color': 'Azul Marino',
                'nro_chapa': 'MNO7890',
                'nro_chasis': 'WVGZZZ2HZKH123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '2967',
                'tipo_combustible': 'Diésel',
                'uso': 'Comercial',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'BR',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },
            {
                'marca': 'Volkswagen',
                'modelo': 'Virtus',
                'anio': 2023,
                'color': 'Blanco Perlado',
                'nro_chapa': 'PQR1234',
                'nro_chasis': '9C2ZZZ12345012345',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1598',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },

            # ==================== FORD ====================
            {
                'marca': 'Ford',
                'modelo': 'Ranger',
                'anio': 2021,
                'color': 'Gris Oscuro',
                'nro_chapa': 'STU5678',
                'nro_chasis': 'MFPEXXKR2MT123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '2198',
                'tipo_combustible': 'Diésel',
                'uso': 'Comercial',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'MANUAL',
                'alarma': True,
                'gps': False,
                'estado': True
            },
            {
                'marca': 'Ford',
                'modelo': 'EcoSport',
                'anio': 2022,
                'color': 'Naranja',
                'nro_chapa': 'VWX9012',
                'nro_chasis': 'MABJWXYZ123456789',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1999',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },
            {
                'marca': 'Ford',
                'modelo': 'Focus',
                'anio': 2019,
                'color': 'Azul',
                'nro_chapa': 'YZA3456',
                'nro_chasis': 'WF0FXXGCD12345678',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1999',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'MANUAL',
                'alarma': False,
                'gps': False,
                'estado': True
            },

            # ==================== CHEVROLET ====================
            {
                'marca': 'Chevrolet',
                'modelo': 'Onix',
                'anio': 2023,
                'color': 'Rojo',
                'nro_chapa': 'BCD7890',
                'nro_chasis': '9BFZL123450123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '998',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': False,
                'estado': True
            },
            {
                'marca': 'Chevrolet',
                'modelo': 'S10',
                'anio': 2022,
                'color': 'Blanco',
                'nro_chapa': 'EFG1234',
                'nro_chasis': '1GCCS196123456789',
                'cantidad_puerta': 4,
                'motor_cilindrada': '2776',
                'tipo_combustible': 'Diésel',
                'uso': 'Comercial',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'BR',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },
            {
                'marca': 'Chevrolet',
                'modelo': 'Tracker',
                'anio': 2021,
                'color': 'Gris',
                'nro_chapa': 'HIJ5678',
                'nro_chasis': 'KLATF08X123456789',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1199',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },

            # ==================== HONDA ====================
            {
                'marca': 'Honda',
                'modelo': 'HR-V',
                'anio': 2023,
                'color': 'Negro',
                'nro_chapa': 'KLM9012',
                'nro_chasis': 'MRHGM123450123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1799',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'JP',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },
            {
                'marca': 'Honda',
                'modelo': 'Civic',
                'anio': 2022,
                'color': 'Plata',
                'nro_chapa': 'NOP3456',
                'nro_chasis': '2HGFG123450123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1996',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'JP',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },

            # ==================== NISSAN ====================
            {
                'marca': 'Nissan',
                'modelo': 'Kicks',
                'anio': 2023,
                'color': 'Azul Celeste',
                'nro_chapa': 'QRS7890',
                'nro_chasis': '3N1CN7AP123456789',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1598',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'JP',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': False,
                'estado': True
            },
            {
                'marca': 'Nissan',
                'modelo': 'Frontier',
                'anio': 2022,
                'color': 'Blanco',
                'nro_chapa': 'TUV1234',
                'nro_chasis': '1N6AD123450123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '2792',
                'tipo_combustible': 'Diésel',
                'uso': 'Comercial',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'JP',
                'tipo_transmision': 'MANUAL',
                'alarma': True,
                'gps': True,
                'estado': True
            },

            # ==================== HYUNDAI ====================
            {
                'marca': 'Hyundai',
                'modelo': 'Creta',
                'anio': 2023,
                'color': 'Blanco',
                'nro_chapa': 'WXY5678',
                'nro_chasis': 'MALBB51S123456789',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1591',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'KR',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },
            {
                'marca': 'Hyundai',
                'modelo': 'Tucson',
                'anio': 2022,
                'color': 'Gris Grafito',
                'nro_chapa': 'ZAB9012',
                'nro_chasis': 'KM8J3CA46NU123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1999',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'KR',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },

            # ==================== KIA ====================
            {
                'marca': 'Kia',
                'modelo': 'Seltos',
                'anio': 2023,
                'color': 'Rojo Pasión',
                'nro_chapa': 'CDE3456',
                'nro_chasis': 'KNAE1234501234567',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1591',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'KR',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },
            {
                'marca': 'Kia',
                'modelo': 'Sportage',
                'anio': 2022,
                'color': 'Azul Marino',
                'nro_chapa': 'FGH7890',
                'nro_chasis': 'KNDPMCAC123456789',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1999',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'IMPORTADO',
                'procedencia': 'KR',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': True,
                'gps': True,
                'estado': True
            },

            # ==================== VEHÍCULOS MÁS ANTIGUOS ====================
            {
                'marca': 'Toyota',
                'modelo': 'Corolla',
                'anio': 2015,
                'color': 'Plateado',
                'nro_chapa': 'IJK1234',
                'nro_chasis': '2T1BU4EE5CC123456',
                'cantidad_puerta': 4,
                'motor_cilindrada': '1794',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'AUTOMATICA',
                'alarma': False,
                'gps': False,
                'estado': True
            },
            {
                'marca': 'Volkswagen',
                'modelo': 'Gol',
                'anio': 2018,
                'color': 'Verde',
                'nro_chapa': 'LMN5678',
                'nro_chasis': '9BWBH51J123456789',
                'cantidad_puerta': 2,
                'motor_cilindrada': '1598',
                'tipo_combustible': 'Nafta',
                'uso': 'Particular',
                'cedula_verde': True,
                'via_importacion': 'LOCAL',
                'procedencia': 'PY',
                'tipo_transmision': 'MANUAL',
                'alarma': False,
                'gps': False,
                'estado': True
            }
        ]

        created_count = 0
        updated_count = 0

        for vehiculo_data in vehiculos:
            nro_chapa = vehiculo_data['nro_chapa']
            nro_chasis = vehiculo_data['nro_chasis']
            
            try:
                # Buscar por número de chapa O número de chasis
                vehiculo = Vehiculo.objects.filter(
                    models.Q(nro_chapa=nro_chapa) | models.Q(nro_chasis=nro_chasis)
                ).first()
                
                if vehiculo:
                    # Actualizar vehículo existente
                    for key, value in vehiculo_data.items():
                        setattr(vehiculo, key, value)
                    
                    # Asignar propietario y poseedor si hay clientes disponibles
                    if clientes and (not vehiculo.propietario or not vehiculo.poseedor):
                        if not vehiculo.propietario:
                            vehiculo.propietario = random.choice(clientes)
                        if not vehiculo.poseedor:
                            # 70% de probabilidad de que el poseedor sea el mismo propietario
                            if random.random() < 0.7:
                                vehiculo.poseedor = vehiculo.propietario
                            else:
                                otros_clientes = [c for c in clientes if c != vehiculo.propietario]
                                if otros_clientes:
                                    vehiculo.poseedor = random.choice(otros_clientes)
                                else:
                                    vehiculo.poseedor = vehiculo.propietario
                    
                    vehiculo.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'⮐ {vehiculo_data["marca"]} {vehiculo_data["modelo"]} - {nro_chapa} (actualizado)'))
                else:
                    # Crear nuevo vehículo
                    vehiculo = Vehiculo.objects.create(**vehiculo_data)
                    
                    # Asignar propietario y poseedor si hay clientes disponibles
                    if clientes:
                        vehiculo.propietario = random.choice(clientes)
                        # 70% de probabilidad de que el poseedor sea el mismo propietario
                        if random.random() < 0.7:
                            vehiculo.poseedor = vehiculo.propietario
                        else:
                            # Evitar que sea el mismo cliente si solo hay uno
                            otros_clientes = [c for c in clientes if c != vehiculo.propietario]
                            if otros_clientes:
                                vehiculo.poseedor = random.choice(otros_clientes)
                            else:
                                vehiculo.poseedor = vehiculo.propietario
                        vehiculo.save()
                    
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ {vehiculo_data["marca"]} {vehiculo_data["modelo"]} - {nro_chapa}'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error con {vehiculo_data["marca"]} {vehiculo_data["modelo"]}: {e}'))

        # Mostrar resumen de asignaciones
        if clientes:
            self.stdout.write(self.style.SUCCESS(f'\nSe asignaron propietarios/poseedores a los vehículos'))
        else:
            self.stdout.write(self.style.WARNING('\nNo se asignaron propietarios/poseedores (no hay clientes activos)'))

        self.stdout.write(self.style.SUCCESS(
            f'\nProceso completado: {created_count} vehículos creados, {updated_count} vehículos actualizados'
        ))
        self.stdout.write(self.style.SUCCESS('Vehículos cargados exitosamente!'))