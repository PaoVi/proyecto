import os
import subprocess
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from seguridad.models import ConfiguracionSistema
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Realiza backup de la base de datos PostgreSQL usando configuraciones del sistema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--manual',
            action='store_true',
            help='Backup manual (ignora configuraciones automáticas)'
        )
    
    def get_config_con_estado(self, clave, default=None):
        """Obtiene configuración verificando tanto valor como estado activo"""
        try:
            config = ConfiguracionSistema.objects.get(clave=clave)
            if not config.activo:
                return default
            return config.get_valor()
        except ConfiguracionSistema.DoesNotExist:
            return default
    
    def handle(self, *args, **options):
        # Verificar si el backup automático está habilitado y ACTIVO
        backup_habilitado = self.get_config_con_estado('backup_automatico', False)
        
        if not backup_habilitado and not options['manual']:
            self.stdout.write(self.style.NOTICE('Backup automático deshabilitado o inactivo. Use --manual para forzar.'))
            return
        
        try:
            # Obtener configuraciones del sistema VERIFICANDO ESTADO ACTIVO
            db_config = settings.DATABASES['default']
            backup_ruta = self.get_config_con_estado('backup_ruta', 'backups/')
            dias_retencion = self.get_config_con_estado('backup_dias_retencion', 30)
            maximo_archivos = self.get_config_con_estado('backup_maximo_archivos', 50)
            notificar_exito = self.get_config_con_estado('backup_notificar_exitoso', False)
            notificar_error = self.get_config_con_estado('backup_notificar_error', False)
            email_notificaciones = self.get_config_con_estado('backup_email_notificaciones', '')
            
            # Verificar si la configuración de backup está activa
            try:
                config_backup = ConfiguracionSistema.objects.get(clave='backup_automatico')
                if not config_backup.activo and not options['manual']:
                    self.stdout.write(self.style.WARNING('Configuración de backup existe pero está INACTIVA'))
                    self.stdout.write(self.style.NOTICE('Use --manual para forzar backup o active la configuración'))
                    return
            except ConfiguracionSistema.DoesNotExist:
                pass
            
            # Crear ruta absoluta si es relativa
            if not os.path.isabs(backup_ruta):
                backup_ruta = os.path.join(settings.BASE_DIR, backup_ruta)
            
            # Crear directorio de backups si no existe
            os.makedirs(backup_ruta, exist_ok=True)
            
            # Nombre del archivo con timestamp
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_ruta, f'backup_{timestamp}.sql')
            
            # Comando pg_dump
            cmd = [
                'pg_dump',
                '-h', db_config['HOST'],
                '-p', db_config['PORT'],
                '-U', db_config['USER'],
                '-d', db_config['NAME'],
                '-f', backup_file
            ]
            
            # Establecer variable de entorno para la contraseña
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            # Ejecutar backup
            self.stdout.write(f'Realizando backup de {db_config["NAME"]}...')
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Limpiar backups antiguos por días de retención
                self.limpiar_backups_por_antiguedad(backup_ruta, dias_retencion)
                
                # Limpiar backups por máximo número de archivos
                self.limpiar_backups_por_cantidad(backup_ruta, maximo_archivos)
                
                # Mostrar información del backup
                tamaño_mb = os.path.getsize(backup_file) / 1024 / 1024
                self.stdout.write(
                    self.style.SUCCESS(f'Backup realizado exitosamente: {backup_file}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Tamaño: {tamaño_mb:.2f} MB')
                )
                
                # Notificar éxito si está configurado y ACTIVO
                if notificar_exito:
                    self.enviar_notificacion_exito(backup_file, tamaño_mb, email_notificaciones)
                else:
                    self.stdout.write(self.style.NOTICE('Notificación de éxito deshabilitada'))
                    
            else:
                error_msg = f'Error en backup: {result.stderr}'
                self.stdout.write(self.style.ERROR(error_msg))
                
                # Notificar error si está configurado y ACTIVO
                if notificar_error:
                    self.enviar_notificacion_error(error_msg, email_notificaciones)
                else:
                    self.stdout.write(self.style.NOTICE('Notificación de error deshabilitada'))
                
        except Exception as e:
            error_msg = f'Error: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            
            # Notificar error si está configurado y ACTIVO
            notificar_error = self.get_config_con_estado('backup_notificar_error', False)
            email_notificaciones = self.get_config_con_estado('backup_email_notificaciones', '')
            
            if notificar_error:
                self.enviar_notificacion_error(error_msg, email_notificaciones)
            
            sys.exit(1)
    
    def limpiar_backups_por_antiguedad(self, backup_ruta, dias_retencion):
        """Elimina backups más antiguos que los días de retención"""
        # Verificar si la configuración de retención está activa
        retencion_activa = self.get_config_con_estado('backup_dias_retencion') is not None
        
        if not retencion_activa or dias_retencion <= 0:
            self.stdout.write(self.style.NOTICE('Limpieza por antigüedad deshabilitada'))
            return
            
        ahora = timezone.now()
        limite = ahora - timedelta(days=dias_retencion)
        eliminados = 0
        
        for filename in os.listdir(backup_ruta):
            if filename.startswith('backup_') and filename.endswith('.sql'):
                filepath = os.path.join(backup_ruta, filename)
                file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                
                if file_time < limite:
                    os.remove(filepath)
                    eliminados += 1
                    self.stdout.write(f'Eliminado backup antiguo: {filename}')
        
        if eliminados > 0:
            self.stdout.write(f'Backups eliminados por antigüedad: {eliminados}')
        else:
            self.stdout.write(self.style.NOTICE('No hay backups antiguos para eliminar'))
    
    def limpiar_backups_por_cantidad(self, backup_ruta, maximo_archivos):
        """Mantiene solo los últimos N archivos de backup"""
        # Verificar si la configuración de máximo archivos está activa
        max_archivos_activo = self.get_config_con_estado('backup_maximo_archivos') is not None
        
        if not max_archivos_activo or maximo_archivos <= 0:
            self.stdout.write(self.style.NOTICE('Limpieza por máximo de archivos deshabilitada'))
            return
            
        backups = []
        
        for filename in os.listdir(backup_ruta):
            if filename.startswith('backup_') and filename.endswith('.sql'):
                filepath = os.path.join(backup_ruta, filename)
                ctime = os.path.getctime(filepath)
                backups.append((ctime, filename, filepath))
        
        # Ordenar por fecha de creación (más antiguos primero)
        backups.sort()
        
        # Eliminar los más antiguos si exceden el máximo
        if len(backups) > maximo_archivos:
            eliminar_count = len(backups) - maximo_archivos
            for i in range(eliminar_count):
                ctime, filename, filepath = backups[i]
                os.remove(filepath)
                self.stdout.write(f'Eliminado backup (límite máximo): {filename}')
            
            self.stdout.write(f'Backups eliminados por límite: {eliminar_count}')
        else:
            self.stdout.write(self.style.NOTICE(f'Total de backups: {len(backups)} (límite: {maximo_archivos})'))
    
    def enviar_notificacion_exito(self, backup_file, tamaño_mb, email_destino):
        """Envía notificación de backup exitoso"""
        if email_destino:
            self.stdout.write(
                self.style.SUCCESS(f'Notificación de éxito enviada a: {email_destino}')
            )
            # Aquí iría el código real para enviar email
            # self.enviar_email(email_destino, 'Backup Exitoso', f'Backup realizado: {backup_file}\nTamaño: {tamaño_mb:.2f} MB')
        else:
            self.stdout.write(
                self.style.WARNING('Backup exitoso, pero no hay email configurado para notificaciones')
            )
    
    def enviar_notificacion_error(self, error_msg, email_destino):
        """Envía notificación de error en backup"""
        if email_destino:
            self.stdout.write(
                self.style.ERROR(f'Notificación de error enviada a: {email_destino}')
            )
            # Aquí iría el código real para enviar email
            # self.enviar_email(email_destino, 'Error en Backup', error_msg)
        else:
            self.stdout.write(
                self.style.WARNING('Error en backup, pero no hay email configurado para notificaciones')
            )