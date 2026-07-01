from django.core.management.base import BaseCommand
from seguridad.models import Usuario

class Command(BaseCommand):
    help = 'Carga usuarios iniciales para el taller Iam Car'

    def handle(self, *args, **options):
        usuarios = [
            # ==================== ADMINISTRADORES ====================
            {
                'username': 'admin',
                'rol': 'admin',
                'is_active': True
            },
            {
                'username': 'sistema',
                'rol': 'admin', 
                'is_active': True
            },

            # ==================== RECEPCIONISTAS ====================
            {
                'username': 'ana',
                'rol': 'recepcion',
                'is_active': True
            },
            {
                'username': 'carlos',
                'rol': 'recepcion',
                'is_active': True
            },
            {
                'username': 'lucia',
                'rol': 'recepcion',
                'is_active': True
            },

            # ==================== MECÁNICOS ====================
            {
                'username': 'juan',
                'rol': 'mecanico',
                'is_active': True
            },
            {
                'username': 'pedro', 
                'rol': 'mecanico',
                'is_active': True
            },
            {
                'username': 'miguel',
                'rol': 'mecanico',
                'is_active': True
            },
            {
                'username': 'roberto',
                'rol': 'mecanico',
                'is_active': True
            },

            # ==================== CHAPISTAS ====================
            {
                'username': 'diego',
                'rol': 'chapista',
                'is_active': True
            },
            {
                'username': 'andres',
                'rol': 'chapista',
                'is_active': True
            },
            {
                'username': 'oscar',
                'rol': 'chapista', 
                'is_active': True
            },

            # ==================== USUARIOS INACTIVOS ====================
            {
                'username': 'maria',
                'rol': 'recepcion',
                'is_active': False
            },
            {
                'username': 'raul',
                'rol': 'mecanico',
                'is_active': False
            }
        ]

        password_comun = 'carsys123'
        created_count = 0
        updated_count = 0
        errores = []

        for usuario_data in usuarios:
            username = usuario_data['username']
            try:
                # Buscar usuario existente
                usuario = Usuario.objects.get(username=username)
                
                # Actualizar usuario existente
                for key, value in usuario_data.items():
                    setattr(usuario, key, value)
                
                usuario.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⮐ {username} - {usuario_data["rol"]} (actualizado)'))
                
            except Usuario.DoesNotExist:
                try:
                    # Crear nuevo usuario - separar username del diccionario
                    username = usuario_data.pop('username')
                    usuario = Usuario.objects.create_user(
                        username=username,
                        password=password_comun,
                        **usuario_data
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ {username} - {usuario_data["rol"]}'))
                    
                except Exception as e:
                    errores.append(f"Error creando {username}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f'✗ {username}: {str(e)}'))
                    
            except Exception as e:
                errores.append(f"Error procesando {username}: {str(e)}")
                self.stdout.write(self.style.ERROR(f'✗ {username}: {str(e)}'))

        # Estadísticas
        total_usuarios = Usuario.objects.count()
        activos = Usuario.objects.filter(is_active=True).count()
        admin_count = Usuario.objects.filter(rol='admin').count()
        recepcion_count = Usuario.objects.filter(rol='recepcion').count()
        mecanico_count = Usuario.objects.filter(rol='mecanico').count()
        chapista_count = Usuario.objects.filter(rol='chapista').count()

        self.stdout.write(self.style.SUCCESS(
            f'\nProceso completado: {created_count} usuarios creados, {updated_count} usuarios actualizados'
        ))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\nErrores encontrados ({len(errores)}):'))
            for error in errores:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Todos los usuarios se procesaron sin errores'))

        self.stdout.write(self.style.SUCCESS(
            f'Total en sistema: {total_usuarios} usuarios ({activos} activos)'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Desglose: {admin_count} administradores, {recepcion_count} recepcionistas, {mecanico_count} mecánicos, {chapista_count} chapistas'
        ))
        self.stdout.write(self.style.SUCCESS(f'Contraseña común para todos: {password_comun}'))
        self.stdout.write(self.style.SUCCESS('Usuarios cargados exitosamente!'))