from django.core.management.base import BaseCommand
from seguridad.models import ConfiguracionSistema

class Command(BaseCommand):
    help = 'Carga configuraciones iniciales del sistema CarSys para Iam Car'

    def handle(self, *args, **options):
        configuraciones = [
            # ==================== 1. DATOS DEL TALLER ====================
            {
                'clave': 'nombre_taller', 
                'valor': 'Iam Car', 
                'tipo': 'string', 
                'grupo': 'datos_taller', 
                'descripcion': 'Nombre del taller mecánico',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'direccion_taller', 
                'valor': 'Av. Automotriz #456, Asunción', 
                'tipo': 'string', 
                'grupo': 'datos_taller', 
                'descripcion': 'Dirección física del taller',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'telefono_taller',
                'valor': '+595 21 123 456', 
                'tipo': 'string', 
                'grupo': 'datos_taller', 
                'descripcion': 'Teléfono de contacto del taller',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'email_contacto', 
                'valor': 'contacto@iamcar.com', 
                'tipo': 'email', 
                'grupo': 'datos_taller', 
                'descripcion': 'Email de contacto principal',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'horario_atencion_lunes_viernes', 
                'valor': '07:00 - 18:00', 
                'tipo': 'string', 
                'grupo': 'datos_taller', 
                'descripcion': 'Horario de atención Lunes a Viernes',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'horario_atencion_sabado', 
                'valor': '08:00 - 12:00', 
                'tipo': 'string', 
                'grupo': 'datos_taller', 
                'descripcion': 'Horario de atención Sábados',
                'editable': True,
                'activo': True
            },
            
            # ==================== DATOS FISCALES ====================
            {
                'clave': 'ruc_taller', 
                'valor': '80012345-1', 
                'tipo': 'string', 
                'grupo': 'datos_fiscales', 
                'descripcion': 'RUC del taller',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'razon_social', 
                'valor': 'IAM CAR S.A.', 
                'tipo': 'string', 
                'grupo': 'datos_fiscales', 
                'descripcion': 'Razón social',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'timbrado_numero', 
                'valor': '12345678', 
                'tipo': 'string', 
                'grupo': 'datos_fiscales', 
                'descripcion': 'Número de timbrado',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'timbrado_vencimiento', 
                'valor': '2026-12-31', 
                'tipo': 'string', 
                'grupo': 'datos_fiscales', 
                'descripcion': 'Fecha de vencimiento del timbrado',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'facturacion', 
                'valor': 'true', 
                'tipo': 'boolean', 
                'grupo': 'datos_fiscales', 
                'descripcion': 'Facturación electrónica',
                'editable': True,
                'activo': True
            },
            
            # ==================== 2. SEGURIDAD - POLÍTICAS ====================
            {
                'clave': 'longitud_minima_password', 
                'valor': '8', 
                'tipo': 'integer', 
                'grupo': 'seguridad', 
                'descripcion': 'Longitud mínima de contraseñas',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'password_complejidad', 
                'valor': 'media', 
                'tipo': 'string', 
                'grupo': 'seguridad', 
                'descripcion': 'Nivel de complejidad de contraseñas (baja/media/alta)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'tiempo_expiracion_sesion', 
                'valor': '120', 
                'tipo': 'integer', 
                'grupo': 'seguridad', 
                'descripcion': 'Tiempo de expiración de sesión en minutos',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'intentos_fallidos_bloqueo', 
                'valor': '10', 
                'tipo': 'integer', 
                'grupo': 'seguridad', 
                'descripcion': 'Intentos fallidos antes de bloqueo de usuario',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'doble_factor_autenticacion', 
                'valor': 'false', 
                'tipo': 'boolean', 
                'grupo': 'seguridad', 
                'descripcion': 'Habilitar autenticación de dos factores',
                'editable': True,
                'activo': True
            },
            
            # ==================== 3. PARÁMETROS DE NEGOCIO ====================
            {
                'clave': 'estados_orden_trabajo', 
                'valor': 'Pendiente,Aprobado,En Reparación,Esperando Repuestos,Finalizada,Entregada,Cancelada', 
                'tipo': 'string', 
                'grupo': 'negocio', 
                'descripcion': 'Estados de órdenes de trabajo (separados por coma)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'categorias_servicios', 
                'valor': 'Mecánica General,Eléctrica,Suspensión y Dirección,Frenos,Motor,Transmisión,Aire Acondicionado', 
                'tipo': 'string', 
                'grupo': 'negocio', 
                'descripcion': 'Categorías de servicios (separadas por coma)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'marcas_vehiculos', 
                'valor': 'Toyota,Volkswagen,Ford,Chevrolet,Honda,Nissan,Hyundai,Kia', 
                'tipo': 'string', 
                'grupo': 'negocio', 
                'descripcion': 'Marcas de vehículos (separadas por coma)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'tipos_vehiculos', 
                'valor': 'Auto,Camioneta,Camión', 
                'tipo': 'string', 
                'grupo': 'negocio', 
                'descripcion': 'Tipos de vehículos (separados por coma)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'metodos_pago', 
                'valor': 'Efectivo,Tarjeta Débito,Tarjeta Crédito,Transferencia Bancaria,Cheque', 
                'tipo': 'string', 
                'grupo': 'negocio', 
                'descripcion': 'Métodos de pago aceptados (separados por coma)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'categorias_insumos', 
                'valor': 'Repuestos Motor,Filtros,Aceites y Lubricantes,Frenos,Suspensión,Eléctricos,Carrocería', 
                'tipo': 'string', 
                'grupo': 'negocio', 
                'descripcion': 'Categorías de insumos (separadas por coma)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'unidades_medida', 
                'valor': 'Unidad,Litro,Kilogramo,Metro,Centímetro,Set', 
                'tipo': 'string', 
                'grupo': 'negocio', 
                'descripcion': 'Unidades de medida (separadas por coma)',
                'editable': True,
                'activo': True
            },
            
            # ==================== 4. NOTIFICACIONES Y COMUNICACIÓN ====================
            {
                'clave': 'notificaciones_habilitadas',
                'valor': 'true',
                'tipo': 'boolean',
                'grupo': 'notificaciones',
                'descripcion': 'Habilita/Deshabilita el envío de correos',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'email_notificaciones_bcc',
                'valor': 'admin@iamcar.com', 
                'tipo': 'email',
                'grupo': 'notificaciones',
                'descripcion': 'Copia oculta para cada notificación enviada',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'smtp_host',
                'valor': 'smtp.gmail.com',
                'tipo': 'string',
                'grupo': 'smtp',
                'descripcion': 'Servidor SMTP',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'smtp_port',
                'valor': '587',              # 587 (TLS) o 465 (SSL)
                'tipo': 'integer',
                'grupo': 'smtp',
                'descripcion': 'Puerto SMTP',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'smtp_use_tls',
                'valor': 'true',             # true si usas 587
                'tipo': 'boolean',
                'grupo': 'smtp',
                'descripcion': 'Usar TLS',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'smtp_use_ssl',
                'valor': 'false',            # true si usas 465 (SSL)
                'tipo': 'boolean',
                'grupo': 'smtp',
                'descripcion': 'Usar SSL',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'smtp_user',
                'valor': 'tu_cuenta@gmail.com',   # la cuenta que autentica con el servidor
                'tipo': 'email',
                'grupo': 'smtp',
                'descripcion': 'Usuario/Correo de autenticación SMTP',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'smtp_password',
                'valor': '',  # contraseña de aplicaciones (Gmail) o password SMTP
                'tipo': 'string',
                'grupo': 'smtp',
                'descripcion': 'Contraseña de aplicaciones o clave SMTP',
                'editable': True,
                'activo': True
            },        
            # ==================== 5. SISTEMA ====================
            {
                'clave': 'moneda_defecto', 
                'valor': 'Gs.', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Moneda por defecto (Guaraníes Paraguayos)',
                'editable': False,
                'activo': True
            },
            {
                'clave': 'idioma_sistema', 
                'valor': 'es', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Idioma del sistema (es, en, pt)',
                'editable': False,
                'activo': True
            },
            {
                'clave': 'formato_fecha', 
                'valor': 'DD/MM/YYYY', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Formato de fecha',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'formato_hora', 
                'valor': 'HH:mm', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Formato de hora',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'zona_horaria', 
                'valor': 'America/Asuncion', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Zona horaria',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'nivel_auditoria', 
                'valor': 'normal', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Nivel de auditoría (minimo/normal/critico/completo)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_automatico', 
                'valor': 'true', 
                'tipo': 'boolean', 
                'grupo': 'sistema', 
                'descripcion': 'Backup automático habilitado',
                'editable': True,
                'activo': True
            },
            
            # ==================== 6. CONFIGURACIONES DE BACKUP ====================
            {
                'clave': 'backup_frecuencia', 
                'valor': 'diario', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Frecuencia de backup: diario, semanal, mensual',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_hora', 
                'valor': '02:00', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Hora para ejecutar backup (formato HH:MM)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_dias_retencion', 
                'valor': '30', 
                'tipo': 'integer', 
                'grupo': 'sistema', 
                'descripcion': 'Días de retención de backups',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_ruta', 
                'valor': 'backups/', 
                'tipo': 'string', 
                'grupo': 'sistema', 
                'descripcion': 'Ruta donde guardar los backups (relativa al proyecto)',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_maximo_archivos', 
                'valor': '50', 
                'tipo': 'integer', 
                'grupo': 'sistema', 
                'descripcion': 'Número máximo de archivos de backup a mantener',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_notificar_exitoso', 
                'valor': 'true', 
                'tipo': 'boolean', 
                'grupo': 'sistema', 
                'descripcion': 'Notificar cuando backup se complete exitosamente',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_notificar_error', 
                'valor': 'true', 
                'tipo': 'boolean', 
                'grupo': 'sistema', 
                'descripcion': 'Notificar cuando ocurra un error en el backup',
                'editable': True,
                'activo': True
            },
            {
                'clave': 'backup_email_notificaciones', 
                'valor': 'sistema@iamcar.com', 
                'tipo': 'email', 
                'grupo': 'sistema', 
                'descripcion': 'Email para notificaciones de backup',
                'editable': True,
                'activo': True
            }
        ]

        for config_data in configuraciones:
            config, created = ConfiguracionSistema.objects.get_or_create(
                clave=config_data['clave'],
                defaults=config_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ {config.clave}'))
            else:
                self.stdout.write(self.style.WARNING(f'⮐ {config.clave} (ya existe)'))

        self.stdout.write(self.style.SUCCESS('\nConfiguraciones de CarSys creadas exitosamente!'))