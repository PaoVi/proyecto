import json
import re
from django.contrib.auth.models import AbstractUser, Permission, Group
from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime


# ==========================
# USUARIOS, ROLES Y PERMISOS
# ==========================
class Usuario(AbstractUser):
    ROLES_BASE = (
        ('admin', 'Administrador'),
        ('mecanico', 'Mecánico'),
        ('chapista', 'Chapista'),
        ('recepcion', 'Recepcionista'),
    )
    
    rol = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_("Rol"),
        error_messages={
            'blank': _("Debe seleccionar un rol."),
        }
    )

    email = models.EmailField(_("email address"), blank=False)
    
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("Teléfono"),
        help_text=_("Formato: +5959XXXXXXX")
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    # Campos heredados de AbstractUser con labels y textos en español
    groups = models.ManyToManyField(
        Group,
        verbose_name=_("Grupos"),
        blank=True,
        help_text=_("Grupos a los que pertenece este usuario."),
        related_name='seguridad_usuario_set',
        related_query_name='usuario',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("Permisos de usuario"),
        blank=True,
        help_text=_("Permisos específicos para este usuario."),
        related_name='seguridad_usuario_permissions_set',  
        related_query_name='usuario',
    )

    class Meta:
        permissions = [
            # USUARIOS
            ("gestionar_usuarios", "Puede gestionar usuarios"),
            ("ver_usuarios", "Puede ver usuarios"),
            ("agregar_usuarios", "Puede agregar usuarios"),
            ("editar_usuarios", "Puede editar usuarios"),
            ("desactivar_usuarios", "Puede desactivar/activar usuarios"),
            
            # ROLES
            ("gestionar_roles", "Puede gestionar roles y permisos"),
            ("ver_roles", "Puede ver roles y permisos"),
            ("agregar_roles", "Puede agregar roles y permisos"),
            ("editar_roles", "Puede editar roles y permisos"),
            ("desactivar_roles", "Puede desactivar/activar roles y permisos"),

            # CONFIGURACIONES
            ("gestionar_configuraciones", "Puede gestionar configuraciones del sistema"),
            ("ver_configuraciones", "Puede ver configuraciones del sistema"),
            ("agregar_configuraciones", "Puede agregar configuraciones del sistema"),
            ("editar_configuraciones", "Puede editar configuraciones del sistema"),
            ("desactivar_configuraciones", "Puede desactivar/activar configuraciones del sistema"),

        ]

    @classmethod
    def obtener_todos_los_roles(cls):
        todos_los_roles = list(cls.ROLES_BASE)
        
        mapeo_roles_base = {nombre: codigo for codigo, nombre in cls.ROLES_BASE}
        
        for group in Group.objects.all():
            grupo_name = group.name
            es_rol_base = False
            
            if grupo_name in mapeo_roles_base:
                es_rol_base = True
            
            grupo_code = grupo_name.lower().replace(' ', '_')
            if grupo_code in dict(cls.ROLES_BASE):
                es_rol_base = True
            
            if not es_rol_base:
                todos_los_roles.append((grupo_name, grupo_name))
        
        return todos_los_roles

    def get_rol_display(self):
        for codigo, nombre in self.ROLES_BASE:
            if codigo == self.rol:
                return nombre
        return self.rol

    def save(self, *args, **kwargs):
        if self.is_superuser and not self.rol:
            self.rol = 'admin'
        super().save(*args, **kwargs)
        self.asignar_grupo_por_rol()
        if kwargs.get('force_insert', False):
            super().save(update_fields=['groups'])

    def asignar_grupo_por_rol(self):
        mapeo_rol_a_grupo = {
            'admin': 'Administrador',
            'mecanico': 'Mecánico', 
            'chapista': 'Chapista',
            'recepcion': 'Recepcionista'
        }
        nombre_grupo = mapeo_rol_a_grupo.get(self.rol, self.rol)
        try:
            grupo = Group.objects.get(name=nombre_grupo)
            self.groups.clear()
            self.groups.add(grupo)
        except Group.DoesNotExist:
            self.groups.clear()

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"


def obtener_permisos_personalizados():
    permisos_usuarios = [
        'gestionar_usuarios',
        'ver_usuarios', 
        'agregar_usuarios',
        'editar_usuarios',
        'desactivar_usuarios'
    ]
    permisos_roles = [
        'gestionar_roles',
        'ver_roles',
        'agregar_roles',
        'editar_roles',
        'desactivar_roles' 
    ]
    permisos_configuraciones = [
        'gestionar_configuraciones',
        'ver_configuraciones',
        'agregar_configuraciones',
        'editar_configuraciones',
        'desactivar_configuraciones',
    ]
    permisos_clientes = [
        'gestionar_clientes',
        'ver_clientes',
        'agregar_clientes',
        'editar_clientes',
        'desactivar_clientes',
    ]
    permisos_empleados = [
        'gestionar_empleados',
        'ver_empleados',
        'agregar_empleados',
        'editar_empleados',
        'desactivar_empleados',
    ]
    permisos_vehiculos = [
        'gestionar_vehiculos',
        'ver_vehiculos',
        'agregar_vehiculos',
        'editar_vehiculos',
        'desactivar_vehiculos',
    ]
    permisos_proveedores = [
        'gestionar_proveedores',
        'ver_proveedores',
        'agregar_proveedores',
        'editar_proveedores',
        'desactivar_proveedoress',
    ]
    permisos_insumos = [
        'gestionar_insumos',
        'ver_insumos',
        'agregar_insumos',
        'editar_insumos',
        'desactivar_insumos',
        'gestionar_stock_insumos',
    ]
    permisos_servicios = [
        'gestionar_servicios',
        'ver_servicios', 
        'agregar_servicios',
        'editar_servicios',
        'desactivar_servicios'
    ]
    permisos_presupuestos = [
        'gestionar_presupuestos',
        'ver_presupuestos',
        'agregar_presupuestos',
        'editar_presupuestos',
        'cambiar_estado_presupuestos',
        'imprimir_presupuestos'
    ]
    permisos_ordenes_trabajo = [
        'gestionar_ordenes_trabajo',
        'ver_ordenes_trabajo',
        'agregar_ordenes_trabajo',
        'editar_ordenes_trabajo',
        'cambiar_estado_ordenes_trabajo',
        'imprimir_ordenes_trabajo'
    ]
    permisos_facturas = [
        'gestionar_facturas',
        'ver_facturas',
        'agregar_facturas',
        'editar_facturas',
        'imprimir_facturas'
    ]
    permisos_compras = [
        'gestionar_compras',
        'agregar_compras',
        'editar_compras',
        'imprimir_compras',
        'anular_compras',
        'reimprimir_compras',
        'recibir_compras',
    ]
    permisos_finanzas = [
        'gestionar_finanzas',
        'ver_finanzas',
        'abrir_caja',
        'cerrar_caja',
        'ver_reportes_financieros',
    ]
    return (permisos_usuarios + 
            permisos_roles + 
            permisos_configuraciones + 
            permisos_clientes + 
            permisos_empleados + 
            permisos_vehiculos + 
            permisos_proveedores +
            permisos_insumos +
            permisos_servicios +
            permisos_presupuestos +
            permisos_ordenes_trabajo +
            permisos_facturas +
            permisos_compras +
            permisos_finanzas
            )


def obtener_permisos_por_categoria():
    return {
        'USUARIOS': [
            'gestionar_usuarios',
            'ver_usuarios', 
            'agregar_usuarios',
            'editar_usuarios',
            'desactivar_usuarios'
        ],
        'ROLES': [
            'gestionar_roles',
            'ver_roles',
            'agregar_roles',
            'editar_roles',
            'desactivar_roles' 
        ],
        'CONFIGURACIONES': [
            'gestionar_configuraciones',
            'ver_configuraciones',
            'agregar_configuraciones',
            'editar_configuraciones',
            'desactivar_configuraciones',
        ],
        'CLIENTES': [
            'gestionar_clientes',
            'ver_clientes',
            'agregar_clientes',
            'editar_clientes',
            'desactivar_clientes',
        ],
        'EMPLEADOS': [
            'gestionar_empleados',
            'ver_empleados',
            'agregar_empleados',
            'editar_empleados',
            'desactivar_empleados',
        ],
        'VEHICULOS': [
            'gestionar_vehiculos',
            'ver_vehiculos',
            'agregar_vehiculos',
            'editar_vehiculos',
            'desactivar_vehiculos',
        ],
        'PROVEEDORES': [
            'gestionar_proveedores',
            'ver_proveedores',
            'agregar_proveedores',
            'editar_proveedores',
            'desactivar_proveedores',
        ],
        'INSUMOS': [
            'gestionar_insumos',
            'ver_insumos', 
            'agregar_insumos',
            'editar_insumos',
            'desactivar_insumos',
            'gestionar_stock_insumos',
        ],
        'SERVICIOS': [
            'gestionar_servicios',
            'ver_servicios',
            'agregar_servicios',
            'editar_servicios',
            'desactivar_servicios',
        ],
        'PRESUPUESTOS': [
            'gestionar_presupuestos',
            'ver_presupuestos',
            'agregar_presupuestos',
            'editar_presupuestos',
            'cambiar_estado_presupuestos',
            'imprimir_presupuestos'
        ],
        'ORDENES_TRABAJO': [
            'gestionar_ordenes_trabajo',
            'ver_ordenes_trabajo',
            'agregar_ordenes_trabajo',
            'editar_ordenes_trabajo',
            'cambiar_estado_ordenes_trabajo',
            'imprimir_ordenes_trabajo'
        ],
        'FACTURAS': [
            'gestionar_facturas',
            'ver_facturas',
            'agregar_facturas',
            'editar_facturas',
            'imprimir_facturas'
        ],
        'COMPRAS': [
            'gestionar_compras',
            'agregar_compras',
            'editar_compras',
            'imprimir_compras',
            'anular_compras',
            'reimprimir_compras',
            'recibir_compras',
        ],
        'FINANZAS': [
            'gestionar_finanzas',
            'ver_finanzas',
            'abrir_caja',
            'cerrar_caja',
            'ver_reportes_financieros',
        ]
    }


@receiver(post_migrate)
def crear_grupos_permisos(sender, **kwargs):
    if sender.name == 'seguridad':
        # Crear permisos personalizados si no existen
        content_type = ContentType.objects.get_for_model(Usuario)
        permisos_personalizados = obtener_permisos_personalizados()
        
        for permiso_codigo in permisos_personalizados:
            permiso, created = Permission.objects.get_or_create(
                codename=permiso_codigo,
                content_type=content_type,
                defaults={'name': permiso_codigo.replace('_', ' ').title()}
            )
        
        # Crear grupos base
        grupos_base = ['Administrador', 'Recepcionista', 'Mecánico', 'Chapista']
        for nombre_grupo in grupos_base:
            grupo, created = Group.objects.get_or_create(name=nombre_grupo)
            if created or nombre_grupo == 'Administrador':
                print(f"Configurando grupo {nombre_grupo}")
                
                if nombre_grupo == 'Administrador':
                    # Asignar TODOS los permisos personalizados al Administrador
                    permisos_admin = Permission.objects.filter(
                        content_type__app_label='seguridad',
                        codename__in=permisos_personalizados
                    )
                    grupo.permissions.set(permisos_admin)
                    grupo.save()
                    print(f"Permisos asignados al Administrador: {grupo.permissions.count()}")

        # Crear permisos para otras apps
        try:
            from cliente.models import Cliente
            content_type_cliente = ContentType.objects.get_for_model(Cliente)
            permisos_cliente = [
                ("gestionar_clientes", "Puede gestionar clientes"),
                ("ver_clientes", "Puede ver clientes"),
                ("agregar_clientes", "Puede registrar clientes"),
                ("editar_clientes", "Puede actualizar clientes"),
                ("desactivar_clientes", "Puede desactivar/activar clientes"),
            ]
            
            for codename, name in permisos_cliente:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_cliente,
                    defaults={'name': name}
                )
            print("Permisos de cliente creados desde seguridad")
        except Exception as e:
            print(f"App cliente no disponible aún: {e}")

        try:
            from empleado.models import Empleado
            content_type_empleado = ContentType.objects.get_for_model(Empleado)
            permisos_empleado = [
                ("gestionar_empleados", "Puede gestionar empleados"),
                ("ver_empleados", "Puede ver empleados"),
                ("agregar_empleados", "Puede registrar empleados"),
                ("editar_empleados", "Puede actualizar empleados"),
                ("desactivar_empleados", "Puede desactivar/activar empleados"),
            ]
            
            for codename, name in permisos_empleado:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_empleado,
                    defaults={'name': name}
                )
            print("Permisos de empleado creados desde seguridad")
        except Exception as e:
            print(f"App empleado no disponible aún: {e}")

        try:
            from vehiculo.models import Vehiculo
            content_type_vehiculo = ContentType.objects.get_for_model(Vehiculo)
            permisos_vehiculo = [
                ("gestionar_vehiculos", "Puede gestionar vehículos"),
                ("ver_vehiculos", "Puede ver vehículos"),
                ("agregar_vehiculos", "Puede registrar vehículos"),
                ("editar_vehiculos", "Puede actualizar vehículos"),
                ("desactivar_vehiculos", "Puede desactivar/activar vehículos"),
            ]
            
            for codename, name in permisos_vehiculo:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_vehiculo,
                    defaults={'name': name}
                )
            print("Permisos de vehiculo creados desde seguridad")
        except Exception as e:
            print(f"App vehiculo no disponible aún: {e}")
        
        try:
            from proveedor.models import Proveedor
            content_type_proveedor = ContentType.objects.get_for_model(Proveedor)
            permisos_proveedor = [
                ("gestionar_proveedores", "Puede gestionar proveedores"),
                ("ver_proveedores", "Puede ver proveedores"),
                ("agregar_proveedores", "Puede registrar proveedores"),
                ("editar_proveedores", "Puede actualizar proveedores"),
                ("desactivar_proveedores", "Puede desactivar/activar proveedores"),
            ]
            
            for codename, name in permisos_proveedor:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_proveedor,
                    defaults={'name': name}
                )
            print("Permisos de proveedor creados desde seguridad")
        except Exception as e:
            print(f"App proveedor no disponible aún: {e}")


        try:
            from insumo.models import Insumo
            content_type_insumo = ContentType.objects.get_for_model(Insumo)
            permisos_insumo= [
                ("gestionar_insumos", "Puede gestionar insumos"),
                ("ver_insumos", "Puede ver insumos"),
                ("agregar_insumos", "Puede registrar insumos"),
                ("editar_insumos", "Puede actualizar insumos"),
                ("desactivar_insumos", "Puede desactivar/activar insumos"),
                ("gestionar_stock_insumos", "Puede gestionar stock de insumos"),
            ]
            
            for codename, name in permisos_insumo:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_insumo,
                    defaults={'name': name}
                )
            print("Permisos de insumo creados desde seguridad")
        except Exception as e:
            print(f"App insumo no disponible aún: {e}")


        try:
            from servicio.models import Servicio
            content_type_servicio = ContentType.objects.get_for_model(Servicio)
            permisos_servicio = [
                ("gestionar_servicios", "Puede gestionar servicios"),
                ("ver_servicios", "Puede ver servicios"),
                ("agregar_servicios", "Puede registrar servicios"),
                ("editar_servicios", "Puede actualizar servicios"),
                ("desactivar_servicios", "Puede desactivar/activar servicios"),
            ]
            
            for codename, name in permisos_servicio:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_servicio,
                    defaults={'name': name}
                )
            print("Permisos de servicio creados desde seguridad")
        except Exception as e:
            print(f"App servicio no disponible aún: {e}")


        try:
            from presupuesto.models import Presupuesto
            content_type_presupuesto = ContentType.objects.get_for_model(Presupuesto)
            permisos_presupuesto = [
                ("gestionar_presupuestos", "Puede gestionar presupuestos"),
                ("ver_presupuestos", "Puede ver presupuestos"),
                ("agregar_presupuestos", "Puede registrar presupuestos"),
                ("editar_presupuestos", "Puede actualizar presupuestos"),
                ("cambiar_estado_presupuestos", "Puede cambiar el estado de presupuestos"), 
                ("imprimir_presupuestos", "Puede imprimir presupuestos"),
            ]
            
            for codename, name in permisos_presupuesto:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_presupuesto,
                    defaults={'name': name}
                )
            print("Permisos de presupuesto creados desde seguridad")
        except Exception as e:
            print(f"App presupuesto no disponible aún: {e}")
        

        try:
            from orden_trabajo.models import OrdenTrabajo
            content_type_orden_trabajo = ContentType.objects.get_for_model(OrdenTrabajo)
            permisos_orden_trabajo= [
                ("gestionar_ordenes_trabajo", "Puede gestionar órdenes de trabajo"),
                ("ver_ordenes_trabajo", "Puede ver órdenes de trabajo"),
                ("agregar_ordenes_trabajo", "Puede registrar órdenes de trabajo"),
                ("editar_ordenes_trabajo", "Puede actualizar órdenes de trabajo"),
                ("cambiar_estado_ordenes_trabajo", "Puede cambiar el estado de órdenes de trabajo"), 
                ("imprimir_ordenes_trabajo", "Puede imprimir órdenes de trabajo"),
            ]
            
            for codename, name in permisos_orden_trabajo:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_orden_trabajo,
                    defaults={'name': name}
                )
            print("Permisos de orden de trabajo creados desde seguridad")
        except Exception as e:
            print(f"App orden de trabajo no disponible aún: {e}") 


        try:
            from factura.models import Factura
            content_type_factura = ContentType.objects.get_for_model(Factura)
            permisos_factura= [
                ("gestionar_facturas", "Puede gestionar facturas"),
                ("ver_facturas", "Puede ver facturas"),
                ("agregar_facturas", "Puede emitir facturas"),
                ("editar_facturas", "Puede actualizar facturas"),
                ("imprimir_facturas", "Puede imprimir facturas"),
                ("anular_facturas", "Puede anular facturas"),
                ("reimprimir_facturas", "Puede reimprimir facturas"),
                ("ver_reportes_facturas", "Puede ver reportes de facturas"),
            ]
            
            for codename, name in permisos_factura:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_factura,
                    defaults={'name': name}
                )
            print("Permisos de factura creados desde seguridad")
        except Exception as e:
            print(f"App factura no disponible aún: {e}")


        try:
            from compra.models import Compra
            content_type_compra = ContentType.objects.get_for_model(Compra)
            permisos_compra= [
                ("gestionar_compras", "Puede gestionar compras"),
                ("ver_compras", "Puede ver compras"),
                ("agregar_compras", "Puede agregar compras"),
                ("editar_compras", "Puede actualizar compras"),
                ("imprimir_compra", "Puede imprimir compras"),
                ("anular_compras", "Puede anular compras"),
                ("reimprimir_compras", "Puede reimprimir compras"),
                ("recibir_compras", "Puede recibir compras"),
            ]
            
            for codename, name in permisos_compra:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_compra,
                    defaults={'name': name}
                )
            print("Permisos de compra creados desde seguridad")
        except Exception as e:
            print(f"App compra no disponible aún: {e}")


        try:
            from finanza.models import Caja
            content_type_finanza = ContentType.objects.get_for_model(Caja)
            permisos_finanza= [
            ("ver_finanzas", "Puede ver finanzas"),
            ("gestionar_finanzas", "Puede gestionar finanzas"),
            ("abrir_caja", "Puede abrir caja"),
            ("cerrar_caja", "Puede cerrar caja"),
            ("ver_reportes_financieros","Puede ver reportes financieros"),
            ]
            
            for codename, name in permisos_finanza:
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type_finanza,
                    defaults={'name': name}
                )
            print("Permisos de finanza creados desde seguridad")
        except Exception as e:
            print(f"App finanza no disponible aún: {e}")
        

# ====================
# PERFILES DE USUARIOS
# ====================
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil')
    intentos_fallidos = models.IntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    requiere_cambio_password = models.BooleanField(default=False)
    ultimo_cambio_password = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = _("Perfil de Usuario")
        verbose_name_plural = _("Perfiles de Usuario")
    
    def __str__(self):
        return f"Perfil de {self.usuario.username}"


# ===========================
# CONFIGURACIONES DEL SISTEMA
# ===========================
class ConfiguracionSistema(models.Model):
    TIPOS_CONFIG = (
        ('string', 'Texto'),
        ('integer', 'Número'),
        ('boolean', 'Si/No'),
        ('email', 'Email'),
        ('json', 'JSON'),
        ('date', 'Fecha'),
    )
    
    clave = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Clave de configuración"),
        error_messages={
            'unique': _("Ya existe una configuración con esa clave."),
        }
    )
    valor = models.TextField(
        verbose_name=_("Valor"),
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPOS_CONFIG,
        default='string',
        verbose_name=_("Tipo de dato"),
        error_messages={
            'invalid_choice': _("Tipo inválido."),
        }
    )
    descripcion = models.TextField(verbose_name=_("Descripción"))
    grupo = models.CharField(max_length=50, default='general', verbose_name=_("Grupo"))
    editable = models.BooleanField(default=True, verbose_name=_("Editable"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Configuración del Sistema")
        verbose_name_plural = _("Configuraciones del Sistema")
        ordering = ['grupo', 'clave']

    def __str__(self):
        return f"{self.clave} ({self.grupo})"

    def get_valor(self):
        """Retorna el valor convertido al tipo correcto"""
        if self.tipo == 'integer':
            return int(self.valor) if self.valor.isdigit() else 0
        elif self.tipo == 'boolean':
            return self.valor.lower() in ('true', '1', 'yes', 'si')
        elif self.tipo == 'json':
            try:
                return json.loads(self.valor)
            except:
                return {}
        elif self.tipo == 'date':
            try:
                return datetime.strptime(self.valor, "%d-%m-%Y").date()
            except Exception:
                return None
        else:
            return self.valor

    @classmethod
    def get_config(cls, clave, default=None):
        try:
            config = cls.objects.get(clave=clave, activo=True) 
            return config.get_valor()
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_config(cls, clave, valor):
        config, created = cls.objects.get_or_create(clave=clave)
        config.valor = str(valor)
        config.save()
        return config             

    def clean(self):
        super().clean()
        if self.clave and not re.fullmatch(r'^[a-z][a-z0-9_]*$', self.clave):
            raise ValidationError({
                'clave': _('La clave debe contener solo letras minúsculas, números y guiones bajos.')
            })
        if self.grupo and not re.fullmatch(r'^[a-z][a-z0-9_]*$', self.grupo):
            raise ValidationError({
                'grupo': _('El grupo debe contener solo letras minúsculas, números y guiones bajos.')
            })
        if self.tipo == 'integer':
            try:
                int(self.valor)
            except ValueError:
                raise ValidationError({
                    'valor': _('Para tipo integer, el valor debe ser un número entero válido')
                })
        elif self.tipo == 'boolean':
            if self.valor.lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'si', 'no'):
                raise ValidationError({
                    'valor': _('Para tipo boolean, el valor debe ser: true, false, 1, 0, yes, no, si, no')
                })
        elif self.tipo == 'date':
            try:
                datetime.strptime(self.valor, "%d-%m-%Y")
            except ValueError:
                raise ValidationError({'valor': _('Para tipo date, el valor debe estar en formato DD-MM-AAAA')})


@receiver(post_migrate)
def inicializar_grupos_existentes(sender, **kwargs):
    if sender.name == 'seguridad':
        for group in Group.objects.all():
            if not hasattr(group, 'activo'):
                group.activo = True
                group.save()


Group.add_to_class('activo', models.BooleanField(default=True, verbose_name=_("Activo")))
Group.add_to_class('fecha_creacion', models.DateTimeField(auto_now_add=True, null=True, verbose_name=_("Fecha de creación")))
Group.add_to_class('fecha_modificacion', models.DateTimeField(auto_now=True, null=True, verbose_name=_("Fecha de modificación")))
