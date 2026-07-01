from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Vaciar la base de datos truncando todas las tablas (¡PELIGROSO!)'
    
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
                    '¡ADVERTENCIA: Esto ELIMINARÁ TODOS LOS DATOS de la base de datos!'
                )
            )
            confirm = input('Escribe "SI" para continuar: ')
            if confirm != 'SI':
                self.stdout.write(self.style.NOTICE('Operación cancelada.'))
                return
        
        try:
            with connection.cursor() as cursor:
                # Obtener todas las tablas
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Excluir django_migrations para mantener las migraciones
                tables = [table for table in tables if table != 'django_migrations']
                
                if not tables:
                    self.stdout.write(self.style.NOTICE('No se encontraron tablas para truncar.'))
                    return
                
                # Truncar todas las tablas
                self.stdout.write(f'Truncando {len(tables)} tablas...')
                
                # Deshabilitar triggers temporalmente
                cursor.execute('SET session_replication_role = replica;')
                
                # Truncar tablas
                for table in tables:
                    cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(f'  - Tabla truncada: {table}')
                
                # Rehabilitar triggers
                cursor.execute('SET session_replication_role = DEFAULT;')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'¡Se truncaron exitosamente {len(tables)} tablas!'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            sys.exit(1)