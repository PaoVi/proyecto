from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import PerfilUsuario, Usuario, ConfiguracionSistema
from empleado.models import Empleado
from django.db.models.signals import post_save, post_delete, pre_save

print("Señales de seguridad cargadas!")

@receiver(post_save, sender=Usuario)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        perfil = PerfilUsuario.objects.create(usuario=instance)
        print(f"Perfil creado automáticamente para: {instance.username}")

@receiver(post_save, sender=Usuario)
def guardar_perfil_usuario(sender, instance, **kwargs):
    if hasattr(instance, 'perfil'):
        instance.perfil.save()
        print(f"Perfil guardado para: {instance.username}")

@receiver(post_save, sender=ConfiguracionSistema)
def limpiar_cache_configuracion(sender, instance, **kwargs):
    # Limpiar cache cuando una configuración se actualiza
    cache.delete(f'config_{instance.clave}')
    print(f"Cache limpiado para configuración: {instance.clave}")

# Variable global para evitar recursión infinita
_syncing = False

@receiver(post_save, sender=Usuario)
def sync_empleado_from_user(sender, instance: Usuario, **kwargs):
    """
    Sincronización bidireccional: Usuario → Empleado
    Cuando se actualiza un usuario, sincroniza con su empleado vinculado
    """
    global _syncing
    
    if _syncing:
        return
        
    emp = getattr(instance, "empleado", None)
    if not emp:
        return
    
    try:
        _syncing = True
        
        update_fields = []
        
        # Sincronizar EMAIL (Usuario → Empleado)
        usr_mail = (instance.email or "").strip()
        emp_mail = (emp.correo_electronico or "").strip()
        if usr_mail and usr_mail != emp_mail:
            emp.correo_electronico = usr_mail
            update_fields.append("correo_electronico")
        
        # Sincronizar TELÉFONO (Usuario → Empleado)
        usr_tel = (instance.telefono or "").strip()
        emp_tel = (emp.telefono or "").strip()
        if usr_tel and usr_tel != emp_tel:
            emp.telefono = usr_tel
            update_fields.append("telefono")  # ← CORREGIDO: "telefono" en inglés
        
        if update_fields:
            emp.save(update_fields=update_fields)
            print(f"DEBUG: Sincronizado Usuario → Empleado: {', '.join(update_fields)}")
            
    finally:
        _syncing = False

@receiver(post_save, sender=Empleado)
def sync_user_from_empleado(sender, instance: Empleado, **kwargs):
    """
    Sincronización bidireccional: Empleado → Usuario  
    Cuando se actualiza un empleado, sincroniza con su usuario vinculado
    """
    global _syncing
    
    if _syncing:
        return
        
    if not instance.user:
        return
    
    try:
        _syncing = True
        
        user = instance.user
        update_fields = []
        
        # Sincronizar EMAIL (Empleado → Usuario)
        emp_mail = (instance.correo_electronico or "").strip()
        usr_mail = (user.email or "").strip()
        if emp_mail and emp_mail != usr_mail:
            user.email = emp_mail
            update_fields.append("email")
        
        # Sincronizar TELÉFONO (Empleado → Usuario)
        emp_tel = (instance.telefono or "").strip()
        usr_tel = (user.telefono or "").strip()
        if emp_tel and emp_tel != usr_tel:
            user.telefono = emp_tel
            update_fields.append("telefono")  # ← CORREGIDO: "telefono" en inglés
        
        if update_fields:
            user.save(update_fields=update_fields)
            print(f"DEBUG: Sincronizado Empleado → Usuario: {', '.join(update_fields)}")
            
    finally:
        _syncing = False

@receiver(post_save, sender=Usuario)
def sync_empleado_email_from_user(sender, instance: Usuario, **kwargs):
    """
    Si el usuario tiene empleado vinculado, empuja su email al correo_electronico del empleado
    cuando sean distintos.
    """
    emp = getattr(instance, "empleado", None)
    if not emp:
        return
    usr_mail = (instance.email or "").strip()
    emp_mail = (emp.correo_electronico or "").strip()
    # Sólo actualizamos si user tiene mail y es diferente
    if usr_mail and usr_mail != emp_mail:
        emp.correo_electronico = usr_mail
        emp.save(update_fields=["correo_electronico"])

# Guardar la clave anterior antes de salvar (por si cambia)
@receiver(pre_save, sender=ConfiguracionSistema)
def _config_guardar_clave_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = ConfiguracionSistema.objects.get(pk=instance.pk)
            instance._old_clave = old.clave
        except ConfiguracionSistema.DoesNotExist:
            instance._old_clave = None

@receiver(post_save, sender=ConfiguracionSistema)
def limpiar_cache_configuracion(sender, instance, **kwargs):
    # borrar cache de la clave actual
    cache.delete(f'config_{instance.clave}')
    # si cambió la clave, borrar también la vieja
    old = getattr(instance, '_old_clave', None)
    if old and old != instance.clave:
        cache.delete(f'config_{old}')

@receiver(post_delete, sender=ConfiguracionSistema)
def limpiar_cache_configuracion_delete(sender, instance, **kwargs):
    cache.delete(f'config_{instance.clave}')