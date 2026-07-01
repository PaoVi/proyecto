from django.core.management.base import BaseCommand
from django.utils import timezone
from seguridad.models import PerfilUsuario

class Command(BaseCommand):
    help = 'Limpiar bloqueos de usuarios expirados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Mostrar información de depuración'
        )

    def handle(self, *args, **options):
        ahora = timezone.now()
        debug = options['debug']
        
        if debug:
            self.stdout.write(f"Hora actual del sistema: {ahora}")
        
        perfiles_bloqueados = PerfilUsuario.objects.filter(
            bloqueado_hasta__isnull=False,
            bloqueado_hasta__lte=ahora
        )
        
        if debug:
            self.stdout.write(f"Usuarios bloqueados encontrados: {perfiles_bloqueados.count()}")
            
            # Listar usuarios que serán limpiados
            for perfil in perfiles_bloqueados:
                self.stdout.write(f"{perfil.usuario.username} - Bloqueado hasta: {perfil.bloqueado_hasta}")
        
        count = perfiles_bloqueados.count()
        resultado = perfiles_bloqueados.update(bloqueado_hasta=None, intentos_fallidos=0)
        
        if debug:
            self.stdout.write(f"Filas afectadas en BD: {resultado}")
        
        self.stdout.write(self.style.SUCCESS(f'{count} bloqueos expirados limpiados'))