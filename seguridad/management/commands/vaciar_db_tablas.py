from django.core.management.base import BaseCommand
from django.db import connection
import sys

class Command(BaseCommand):
    help = 'Vaciar datos de tablas específicas sin afectar migraciones (¡PELIGROSO!)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', 
            '--no-input',
            action='store_true',
            help='Omitir confirmación',
        )
    
    def handle(self, *args, **options):
        # Confirmación de seguridad
        if not options['noinput']:
            self.stdout.write(
                self.style.WARNING(
                    '¡ADVERTENCIA: Esto ELIMINARÁ LOS DATOS de las tablas especificadas!'
                )
            )
            confirm = input('Escribe "SI" para continuar: ')
            if confirm != 'SI':
                self.stdout.write(self.style.NOTICE('Operación cancelada.'))
                return

        # Lista de tablas a vaciar
        tablas_a_vaciar = ['insumo_insumo']  # Añade aquí las tablas que quieras vaciar

        try:
            with connection.cursor() as cursor:
                # Deshabilitar triggers temporalmente
                cursor.execute('SET session_replication_role = replica;')
                
                # Vaciar tablas
                for tabla in tablas_a_vaciar:
                    cursor.execute(f'TRUNCATE TABLE "{tabla}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(f'  - Tabla truncada: {tabla}')
                
                # Rehabilitar triggers
                cursor.execute('SET session_replication_role = DEFAULT;')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'¡Se vaciaron exitosamente {len(tablas_a_vaciar)} tablas!'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            sys.exit(1)
