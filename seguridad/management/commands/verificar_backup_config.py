from django.core.management.base import BaseCommand
from seguridad.models import ConfiguracionSistema

class Command(BaseCommand):
    help = 'Verifica las configuraciones de backup del sistema incluyendo estado activo'
    
    def handle(self, *args, **options):
        configs = [
            'backup_automatico',
            'backup_frecuencia', 
            'backup_hora',
            'backup_dias_retencion',
            'backup_ruta',
            'backup_maximo_archivos',
            'backup_notificar_exitoso',
            'backup_notificar_error',
            'backup_email_notificaciones'
        ]
        
        self.stdout.write('Verificando configuraciones de backup (valor + estado)...\n')
        
        for config_key in configs:
            try:
                config_obj = ConfiguracionSistema.objects.get(clave=config_key)
                valor = config_obj.get_valor()
                estado = 'ACTIVO' if config_obj.activo else 'INACTIVO'
                estado_icon = 'SI' if config_obj.activo else 'NO'
                
                self.stdout.write(f'{estado_icon} {config_key}: {valor} ({estado})')
                
                if config_obj.descripcion:
                    self.stdout.write(f'{config_obj.descripcion}')
                    
            except ConfiguracionSistema.DoesNotExist:
                self.stdout.write(f'{config_key}: NO CONFIGURADO')
            
            self.stdout.write('')
        
        # Verificar estado general del backup
        try:
            config_backup = ConfiguracionSistema.objects.get(clave='backup_automatico')
            if config_backup.activo and config_backup.get_valor():
                self.stdout.write(self.style.SUCCESS('Backup automático: HABILITADO Y ACTIVO'))
            elif config_backup.get_valor() and not config_backup.activo:
                self.stdout.write(self.style.WARNING('Backup automático: VALOR=SÍ pero INACTIVO'))
            else:
                self.stdout.write(self.style.NOTICE('Backup automático: DESHABILITADO'))
                
        except ConfiguracionSistema.DoesNotExist:
            self.stdout.write(self.style.ERROR('Configuración de backup automático no existe'))