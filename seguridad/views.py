from django.forms import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from sqlite3 import IntegrityError
from django.contrib import messages 
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import authenticate, login, logout
from empleado.models import Empleado
from seguridad.forms import ConfiguracionBusquedaForm, ConfiguracionForm, ConfiguracionEditarForm, UsuarioForm, UsuarioEditarForm, PerfilUsuarioForm, RolPermisosForm, EmailNotificacionesForm
from .models import ConfiguracionSistema, Usuario
from django.core.paginator import Paginator 
from .utils import obtener_configuracion 
from .forms import UsuarioAsignarEmpleadoForm
from django.db.models import Q


# =============
# LOGIN, LOGOUT
# =============
def home(request):
    return render(request, 'seguridad/home.html')


def login_view(request):
    error_message = None
    username = ''
    intentos_restantes = None

    next_url = request.GET.get('next', 'home')

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        next_url = request.POST.get('next', 'home')
        # Obtener configuraciones de seguridad
        max_intentos = obtener_configuracion('intentos_fallidos_bloqueo', 5)
        tiempo_bloqueo = obtener_configuracion('tiempo_bloqueo_usuario', 30)

        # Verificar si el usuario existe
        try:
            user_obj = Usuario.objects.get(username=username)
            
            # Verificar si está bloqueado
            if hasattr(user_obj, 'perfil') and user_obj.perfil.bloqueado_hasta:
                if user_obj.perfil.bloqueado_hasta > timezone.now():
                    tiempo_restante = user_obj.perfil.bloqueado_hasta - timezone.now()
                    minutos_restantes = int(tiempo_restante.total_seconds() / 60)
                    error_message = f'Usuario bloqueado. Intente nuevamente en {minutos_restantes} minutos.'
                    return render(request, "seguridad/login.html", {
                        "error_message": error_message,
                        "username": username,
                        "next": next_url
                    })
            
            # Verificar si está inactivo
            if not user_obj.is_active:
                error_message = "Usuario inactivo. Contacte al administrador."
                return render(request, "seguridad/login.html", {
                    "error_message": error_message,
                    "username": username,
                    "next": next_url
                })
                
        except Usuario.DoesNotExist:
            # Usuario no existe (seguimos a authenticate para mensaje genérico)
            pass

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                error_message = "Usuario inactivo. Contacte al administrador."
                return render(request, "seguridad/login.html", {
                    "error_message": error_message,
                    "username": username,
                    "next": next_url
                })
            else:
                # Reiniciar contador de intentos fallidos si existe perfil
                if hasattr(user, 'perfil'):
                    user.perfil.intentos_fallidos = 0
                    user.perfil.bloqueado_hasta = None
                    user.perfil.save()
                
                # Login
                login(request, user)
                
                # Marcar actividad inicial (fundamental para timeout dinámico)
                request.session['last_activity'] = timezone.now().isoformat()
                
                # Actualizar último acceso
                user.ultimo_acceso = timezone.now()
                user.save()

                # Asignar sucursal activa en la sesión
                perfil = getattr(user, 'perfil', None)
                if perfil and perfil.sucursal_activa:
                    request.session['sucursal_id'] = perfil.sucursal_activa_id
                else:
                    from sucursal.models import Sucursal
                    sucursal_default = Sucursal.objects.filter(activo=True).first()
                    if sucursal_default:
                        request.session['sucursal_id'] = sucursal_default.id

                messages.success(request, f"Bienvenido {user.username}!")
                return redirect(next_url)
        else:
            # Manejar intentos fallidos solo si el usuario existe
            try:
                user_obj = Usuario.objects.get(username=username)
                if hasattr(user_obj, 'perfil'):
                    user_obj.perfil.intentos_fallidos += 1
                    
                    # Bloquear usuario si excede los intentos
                    if user_obj.perfil.intentos_fallidos >= max_intentos:
                        user_obj.perfil.bloqueado_hasta = timezone.now() + timedelta(minutes=tiempo_bloqueo)
                        user_obj.perfil.save()
                        error_message = f'Demasiados intentos fallidos. Usuario bloqueado por {tiempo_bloqueo} minutos.'
                    else:
                        intentos_restantes = max_intentos - user_obj.perfil.intentos_fallidos
                        error_message = 'Usuario o contraseña incorrecta.'
                    
                    user_obj.perfil.save()
                else:
                    intentos_restantes = max_intentos - 1
                    error_message = 'Usuario o contraseña incorrecta.'
                    
            except Usuario.DoesNotExist:
                error_message = "Usuario inexistente"

    return render(request, "seguridad/login.html", {
        'error_message': error_message,
        'username': username,
        'intentos_restantes': intentos_restantes,
        "next": next_url
    })


def exit(request):
    logout(request)
    messages.info(request, "Sesión Cerrada")
    return redirect('home')


# ========
# USUARIOS
# ========
@login_required
@permission_required('seguridad.agregar_usuarios', raise_exception=True)
def usuario_crear(request):
    if request.method == "POST":
        formulario = UsuarioForm(request.POST, user=request.user)
        if formulario.is_valid():
            try:
                usuario = formulario.save()
                messages.success(request, f'Usuario {usuario.username} creado')
                return redirect('usuario_lista')
            except IntegrityError:
                messages.error(request, 'Error: El nombre de usuario ya existe')
        else:
            # Solo volvemos a renderizar para que se vean debajo del input
            pass
    else:
        formulario = UsuarioForm(user=request.user)

    roles = Group.objects.all()
    return render(request, 'seguridad/usuario_crear.html', {
        'formulario': formulario,
        'roles': roles
    })


@login_required
@permission_required('seguridad.ver_usuarios', raise_exception=True)
def usuario_ver(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    permisos = usuario.get_all_permissions()
    return render(request, 'seguridad/usuario_ver.html', {
        'usuario': usuario,
        'permisos': permisos
    })


@login_required
@permission_required('seguridad.editar_usuarios', raise_exception=True)
def usuario_editar(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    
    es_propio_usuario = usuario.id == request.user.id
    puede_desactivar_usuarios = request.user.has_perm('seguridad.desactivar_usuarios') and not es_propio_usuario
    
    if request.method == "POST":
        print(f"DEBUG: POST data: {request.POST}")
        print(f"DEBUG: Usuario antes de editar - Email: {usuario.email}, Teléfono: {usuario.telefono}")
        
        # Pasar el request al formulario
        formulario = UsuarioEditarForm(request.POST, instance=usuario, user=request.user, request=request)
        
        if formulario.is_valid():
            print(f"DEBUG: Formulario válido. Datos: {formulario.cleaned_data}")
            try:
                usuario_editado = formulario.save()
                print(f"DEBUG: Usuario después de guardar - Email: {usuario_editado.email}, Teléfono: {usuario_editado.telefono}")
                
                # Verificar si hay empleado vinculado y sincronizar
                try:
                    empleado_vinculado = Empleado.objects.get(user=usuario_editado)
                    print(f"DEBUG: Empleado vinculado encontrado: {empleado_vinculado.nombre}")
                    print(f"DEBUG: Datos empleado - Email: {empleado_vinculado.correo_electronico}, Teléfono: {empleado_vinculado.telefono}")
                except Empleado.DoesNotExist:
                    print(f"DEBUG: No hay empleado vinculado")
                
                messages.success(request, f'Usuario {usuario.username} actualizado')
                return redirect('usuario_lista')
                    
            except IntegrityError:
                messages.error(request, 'Error: El nombre de usuario ya existe')
            except ValidationError as e:
                messages.error(request, f'Error de validación: {e}')
        else:
            print(f"DEBUG: Formulario inválido. Errores: {formulario.errors}")
    else:
        print(f"DEBUG: Cargando formulario GET. Usuario actual - Email: {usuario.email}, Teléfono: {usuario.telefono}")
        # Pasar el request al formulario también en GET
        formulario = UsuarioEditarForm(instance=usuario, user=request.user, request=request)

    roles = Group.objects.all()
    return render(request, 'seguridad/usuario_editar.html', {
        'form': formulario,
        'usuario': usuario,
        'roles': roles,
        'puede_desactivar_usuarios': puede_desactivar_usuarios,
        'es_propio_usuario': es_propio_usuario,
    })


@login_required
@permission_required('seguridad.desactivar_usuarios', raise_exception=True)
def usuario_desactivar(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    
    # No permitir desactivarse a sí mismo
    if usuario == request.user:
        messages.error(request, 'No puedes desactivar tu propio usuario')
        return redirect('usuario_lista')
    
    usuario.is_active = not usuario.is_active
    usuario.save()
    estado = 'activado' if usuario.is_active else 'desactivado'
    messages.success(request, f'Usuario {usuario.username} {estado}')
    return redirect('usuario_lista') 


@login_required
@permission_required('seguridad.ver_usuarios', raise_exception=True)
def usuario_lista(request):
    username_query = request.GET.get('username', '')
    rol_query = request.GET.get('rol', '')
    estado_query = request.GET.get('estado', '') 
    
    usuarios = Usuario.objects.all().order_by('username')
    
    if username_query:
        usuarios = usuarios.filter(username__icontains=username_query)
    if rol_query:
        usuarios = usuarios.filter(rol=rol_query)
    if estado_query:
        if estado_query == 'activo':
            usuarios = usuarios.filter(is_active=True) 
        elif estado_query == 'inactivo':
            usuarios = usuarios.filter(is_active=False)

    # Obtener todos los roles disponibles dinámicamente
    roles_disponibles = Usuario.obtener_todos_los_roles()
    
    # PAGINACIÓN - 10 elementos por página
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    usuarios = paginator.get_page(page_number)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()
    
    return render(request, 'seguridad/usuario_lista.html', {
        'usuarios': usuarios,
        'roles': roles_disponibles,
        'qs_no_page': qs_no_page,
    })


@login_required
@permission_required('seguridad.editar_empleados', raise_exception=True)
def usuario_asignar_empleado(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)

    if request.method == "POST":
        form = UsuarioAsignarEmpleadoForm(request.POST, usuario=usuario)
        if form.is_valid():
            empleado = form.cleaned_data["empleado"]
            empleado.user = usuario
            empleado.save(update_fields=["user"])
            messages.success(request, f"Empleado {empleado.nombre} vinculado")
            return redirect("usuario_ver", usuario.pk)
    else:
        form = UsuarioAsignarEmpleadoForm(usuario=usuario)

    return render(request, "seguridad/usuario_asignar_empleado.html", {
        "usuario": usuario,
        "form": form,
    })


@login_required
@permission_required('seguridad.editar_usuarios', raise_exception=True)
def usuario_eliminar_empleado(request, usuario_id):
    if request.method == "POST":
        usuario = get_object_or_404(Usuario, pk=usuario_id)
        
        # Buscar el empleado vinculado a este usuario
        from empleado.models import Empleado
        try:
            empleado = Empleado.objects.get(user=usuario)
            
            # Guardar información antes de desvincular
            empleado_nombre = empleado.nombre
            usuario_email = usuario.email
            usuario_telefono = usuario.telefono
            
            print(f"DEBUG: Antes de desvincular - Usuario email: {usuario_email}, teléfono: {usuario_telefono}")
            
            # IMPORTANTE: Mantener los datos en el empleado antes de desvincular
            # Si el empleado no tiene email pero el usuario sí, mantenerlo en el empleado
            if not empleado.correo_electronico and usuario_email:
                empleado.correo_electronico = usuario_email
                print(f"DEBUG: Copiando email del usuario al empleado: {usuario_email}")
            
            # Si el empleado no tiene teléfono pero el usuario sí, mantenerlo en el empleado
            if not empleado.telefono and usuario_telefono:
                empleado.telefono = usuario_telefono
                print(f"DEBUG: Copiando teléfono del usuario al empleado: {usuario_telefono}")
            
            # Guardar los cambios en el empleado primero
            empleado.save()
            print(f"DEBUG: Empleado guardado - Email: {empleado.correo_electronico}, Teléfono: {empleado.telefono}")
            
            # Ahora limpiar los datos del usuario
            usuario.email = ""
            usuario.telefono = ""
            
            print(f"DEBUG: Después de limpiar - Usuario email: '{usuario.email}', teléfono: '{usuario.telefono}'")
            
            # Guardar el usuario con datos limpios
            usuario.save(update_fields=["email", "telefono"])
            print(f"DEBUG: Usuario guardado con campos limpios")
            
            # Finalmente desvincular el empleado
            empleado.user = None
            empleado.save(update_fields=["user"])
            print(f"DEBUG: Empleado desvinculado")
            
            messages.success(request, f"Empleado {empleado_nombre} desvinculado")
            
        except Empleado.DoesNotExist:
            # No hay empleado vinculado
            messages.info(request, "El usuario no tiene empleado vinculado")
        
        return redirect('usuario_editar', usuario_id=usuario_id)
    return redirect('usuario_editar', usuario_id=usuario_id)


@login_required
def buscar_empleados_vincular(request):
    """Vista para autocompletar empleados - SOLO EMPLEADOS SIN USUARIO"""
    query = request.GET.get('q', '').strip()
    contexto = request.GET.get('contexto', 'general')
    
    try:
        # Base query - empleados activos
        empleados = Empleado.objects.filter(estado=True)
        
        # FILTRAR POR CONTEXTO - para asignación, solo empleados sin usuario
        if contexto == 'asignacion':
            # Excluir empleados que YA tienen usuario asociado
            empleados = empleados.filter(user__isnull=True)
        
        # Aplicar filtro de búsqueda si hay query
        if query:
            empleados = empleados.filter(
                Q(cedula_ruc__icontains=query) |
                Q(nombre__icontains=query) |
                Q(cargo__icontains=query)
            )
        
        # Ordenar y limitar resultados
        empleados = empleados.order_by('nombre')[:10]
        
        # Formatear respuesta
        empleados_data = []
        for empleado in empleados:
            empleados_data.append({
                'id': empleado.pk,
                'text': f"{empleado.cedula_ruc} - {empleado.nombre}",
                'cedula': empleado.cedula_ruc or 'Sin cédula',
                'nombre': empleado.nombre or 'Sin nombre',
                'cargo': empleado.cargo or 'Sin cargo',
            })
        
        return JsonResponse(empleados_data, safe=False)
        
    except Exception as e:
        print(f"Error en búsqueda de empleados: {e}")
        return JsonResponse([], safe=False)
    
# ================
# ROLES Y PERMISOS
# ================
@login_required
@permission_required('seguridad.agregar_roles', raise_exception=True)
def rol_crear(request):
    if request.method == 'POST':
        form = RolPermisosForm(request.POST)
        if form.is_valid():
            grupo = form.save()
            messages.success(request, f'Rol {grupo.name} creado')
            return redirect('rol_lista')
    else:
        form = RolPermisosForm(initial={'activo': True})
    
    return render(request, 'seguridad/rol_crear.html', {'form': form})


@login_required
@permission_required('seguridad.ver_roles', raise_exception=True)
def rol_ver(request, grupo_id):
    grupo = get_object_or_404(Group, id=grupo_id)
    
    usuarios = grupo.seguridad_usuario_set.all() 
    
    context = {
        'grupo': grupo,
        'usuarios': usuarios
    }
    return render(request, 'seguridad/rol_ver.html', context)


@login_required
@permission_required('seguridad.editar_roles', raise_exception=True)
def rol_editar(request, grupo_id):
    from django.contrib.auth.models import Group

    grupo = get_object_or_404(Group, pk=grupo_id)

    # Verificar si el usuario tiene permiso para desactivar roles
    puede_desactivar_roles = request.user.has_perm('seguridad.desactivar_roles')
    usuarios_count = grupo.seguridad_usuario_set.count()

    if request.method == 'POST':
        form = RolPermisosForm(request.POST, instance=grupo)

        # Permisos seleccionados para re-render (si hay error)
        try:
            selected_ids = [int(x) for x in request.POST.getlist('permisos')]
        except ValueError:
            selected_ids = []

        if form.is_valid():
            # Regla: no permitir desactivar si tiene usuarios
            usuarios_asignados = grupo.seguridad_usuario_set.count()
            activo_val = form.cleaned_data.get('activo', True)
            
            if usuarios_asignados > 0 and not activo_val:
                # Error a nivel de campo (no permite guardar)
                form.add_error('activo', 'No se puede desactivar este rol porque tiene usuarios asignados.')
            elif not puede_desactivar_roles and not activo_val:
                # Si no tiene permisos y está intentando desactivar, mantener el valor actual
                grupo.activo = grupo.activo 
                form.save()
                messages.success(request,f'Rol {grupo.name} actualizado')
                return redirect('rol_lista')
            else:
                form.save()
                messages.success(request,f'Rol {grupo.name} actualizado')
                return redirect('rol_lista')
    else:
        form = RolPermisosForm(instance=grupo)
        selected_ids = list(grupo.permissions.values_list('id', flat=True))

    # queryset ordenado + agrupable por app
    permisos_qs = (
        form.fields['permisos']
        .queryset.select_related('content_type')
        .order_by('content_type__app_label', 'name')
    )

    return render(
        request,
        'seguridad/rol_editar.html',
        {
            'form': form,
            'grupo': grupo,
            'permisos_qs': permisos_qs,
            'selected_ids': selected_ids,
            'puede_desactivar_roles': puede_desactivar_roles,
            'usuarios_count': usuarios_count,
        }
    )


@login_required
@permission_required('seguridad.desactivar_roles', raise_exception=True)
def rol_desactivar(request, grupo_id):
    grupo = get_object_or_404(Group, pk=grupo_id)

    # Prevenir desactivación de roles críticos
    roles_criticos = ["Administrador", "Mecánico", "Chapista", "Recepcionista"]
    if grupo.name in roles_criticos:
        messages.error(request, f'No se puede desactivar el rol {grupo.name}.')
        return redirect('rol_lista')

    # Mapeo inverso: nombre de grupo a código de rol
    mapeo_grupo_a_rol = {
        'Administrador': 'admin',
        'Mecánico': 'mecanico', 
        'Chapista': 'chapista',
        'Recepcionista': 'recepcion'
    }

    # Verificar usuarios asignados al GRUPO (no al campo rol)
    usuarios_asignados = grupo.seguridad_usuario_set.count()
    
    if usuarios_asignados > 0:
        messages.error(request, f'No se puede desactivar el rol {grupo.name} porque tiene {usuarios_asignados} usuario(s) asignado(s).')
        return redirect('rol_lista')
    
    # Cambiar estado activo/inactivo
    grupo.activo = not grupo.activo
    grupo.save()
    
    estado = 'activado' if grupo.activo else 'desactivado'
    messages.success(request, f'Rol {grupo.name} {estado}')
    return redirect('rol_lista')


@login_required
@permission_required('seguridad.ver_roles', raise_exception=True)
def rol_lista(request):
    # Obtener parámetros de búsqueda y filtro
    nombre_query = request.GET.get('nombre', '')
    estado_query = request.GET.get('estado', '')
    
    # Consulta base con filtro de estado
    if estado_query == 'activo':
        grupos = Group.objects.filter(activo=True)
    elif estado_query == 'inactivo':
        grupos = Group.objects.filter(activo=False)
    else:
        grupos = Group.objects.all()
    
    # Aplicar filtro de nombre si existe
    if nombre_query:
        grupos = grupos.filter(name__icontains=nombre_query)
    
    grupos = grupos.order_by('name')
    
    # PAGINACIÓN - 10 elementos por página
    paginator = Paginator(grupos, 10)
    page_number = request.GET.get('page')
    grupos = paginator.get_page(page_number)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()
    
    return render(request, 'seguridad/rol_lista.html', {
        'grupos': grupos,
        'estado_filtro': estado_query,
        'nombre_busqueda': nombre_query,
        'qs_no_page': qs_no_page,
    })


# ====================
# PERFILES DE USUARIOS
# ====================
@login_required
def perfil_usuario(request):
    # Forzar la recarga del usuario desde la base de datos
    usuario = Usuario.objects.get(pk=request.user.pk)
    
    # Obtener todos los permisos únicos del usuario
    permisos_set = set()
    for group in usuario.groups.all():
        permisos_set.update(group.permissions.all())
    permisos_set.update(usuario.user_permissions.all())
    
    # Ordenados y filtrados
    permisos = sorted(permisos_set, key=lambda x: x.name)
    permisos_personalizados = [
        permiso for permiso in permisos 
        if permiso.content_type.app_label == 'seguridad'
    ]
    
    return render(request, 'seguridad/perfil.html', {
        'usuario': usuario,
        'permisos': permisos_personalizados
    })


@login_required
def perfil_usuario_editar(request):
    # Forzar la recarga del usuario desde la base de datos para obtener datos actualizados
    usuario = Usuario.objects.get(pk=request.user.pk)
    
    if request.method == "POST":
        form = PerfilUsuarioForm(request.POST, instance=usuario)
        
        if form.is_valid():
            try:
                usuario_actualizado = form.save()
                messages.success(request, 'Perfil actualizado')
                
                # Si cambió la contraseña, mantener la sesión
                if 'new_password' in form.cleaned_data and form.cleaned_data['new_password']:
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, usuario_actualizado)
                    messages.info(request, 'Su sesión se mantuvo activa después del cambio de contraseña')
                
                return redirect('perfil_usuario')
            except ValidationError as e:
                # Agregar errores al formulario directamente
                form.add_error(None, e)
            except Exception as e:
                print(f"Error inesperado: {e}")
                form.add_error(None, "Ocurrió un error inesperado al actualizar el perfil.")
    else:
        form = PerfilUsuarioForm(instance=usuario)
    
    return render(request, 'seguridad/perfil_editar.html', {
        'form': form,
        'usuario': usuario,
    })


# ===========================
# CONFIGURACIONES DEL SISTEMA
# ===========================
@login_required
@permission_required('seguridad.agregar_configuraciones', raise_exception=True)
def configuracion_crear(request):
    if request.method == 'POST':
        form = ConfiguracionForm(request.POST)
        if form.is_valid():
            configuracion = form.save()
            messages.success(request, f"Configuración {configuracion.clave} creada")
            return redirect('configuracion_lista')
    else:
        form = ConfiguracionForm()
    
    return render(request, 'seguridad/configuracion_crear.html', {'form': form})


@login_required
@permission_required('seguridad.ver_configuraciones', raise_exception=True)
def configuracion_ver(request, config_id):
    configuracion = get_object_or_404(ConfiguracionSistema, id=config_id)
    return render(request, 'seguridad/configuracion_ver.html', {
        'configuracion': configuracion
    })


@login_required
@permission_required('seguridad.editar_configuraciones', raise_exception=True)
def configuracion_editar(request, config_id):
    configuracion = get_object_or_404(ConfiguracionSistema, id=config_id)

    puede_desactivar_configuraciones = request.user.has_perm('seguridad.desactivar_configuraciones')

    if not configuracion.editable:
        messages.error(request, "Esta configuración no es editable")
        return redirect('configuracion_lista')

    if request.method == 'POST':
        form = ConfiguracionEditarForm(request.POST, instance=configuracion)
        if form.is_valid():
            try:
                form.save()
                messages.success(request,f"Configuración {configuracion.clave} actualizada")
                return redirect('configuracion_lista')
            except ValidationError as e:
                for field, errors in e.error_dict.items():
                    for error in errors:
                        form.add_error(field, error)
    else:
        form = ConfiguracionEditarForm(instance=configuracion)

    return render(request, 'seguridad/configuracion_editar.html', {
        'form': form,
        'configuracion': configuracion,
        'puede_desactivar_configuraciones' : puede_desactivar_configuraciones,
    })


@login_required
@permission_required('seguridad.desactivar_configuraciones', raise_exception=True)
def configuracion_desactivar(request, config_id):
    config = get_object_or_404(ConfiguracionSistema, pk=config_id)
    
    # Verificar si es editable
    if not config.editable:
        messages.error(request, 'Esta configuración no es editable')
        return redirect('configuracion_lista')
    
    # Cambiar el estado
    config.activo = not config.activo
    config.save()
    
    estado = 'activada' if config.activo else 'desactivada'
    messages.success(request, f'Configuración {config.clave} {estado}')
    
    return redirect('configuracion_lista')


@login_required
@permission_required('seguridad.ver_configuraciones', raise_exception=True)
def configuracion_lista(request):
    form_busqueda = ConfiguracionBusquedaForm(request.GET or None)
    configuraciones = ConfiguracionSistema.objects.all().order_by('grupo', 'clave')
    
    # Aplicar filtros si existen
    grupo_query = request.GET.get('grupo')
    clave_query = request.GET.get('clave')
    estado_query = request.GET.get('estado') 
    
    if grupo_query:
        configuraciones = configuraciones.filter(grupo=grupo_query)
    if clave_query:
        configuraciones = configuraciones.filter(clave__icontains=clave_query)
    if estado_query:
        if estado_query == 'activo':
            configuraciones = configuraciones.filter(activo=True)
        elif estado_query == 'inactivo':
            configuraciones = configuraciones.filter(activo=False)
    
    # PAGINACIÓN - 10 elementos por página
    paginator = Paginator(configuraciones, 10) 
    page_number = request.GET.get('page')
    configuraciones = paginator.get_page(page_number)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()
    
    # Obtener grupos únicos para la sección de badges
    grupos_unicos = ConfiguracionSistema.objects.values_list('grupo', flat=True).distinct().order_by('grupo')
    
    context = {
        'configuraciones': configuraciones,
        'form_busqueda': form_busqueda,
        'grupos_unicos': grupos_unicos,
        'estado_actual': estado_query,
        'qs_no_page': qs_no_page,
    }
    
    return render(request, 'seguridad/configuracion_lista.html', context)


# ==============
# NOTIFICACIONES
# ==============
@login_required
@permission_required('seguridad.editar_configuraciones', raise_exception=True)
def configuracion_email_notificaciones(request):
    """
    Pantalla para editar la clave 'email_notificaciones' en ConfiguracionSistema.
    """
    clave = "email_notificaciones"
    conf = ConfiguracionSistema.objects.filter(clave=clave).first()

    initial = {}
    if conf:
        initial = {
            "email_notificaciones": (conf.valor or "").strip(),
            "activo": conf.activo,
        }

    if request.method == "POST":
        form = EmailNotificacionesForm(request.POST, initial=initial)
        if form.is_valid():
            email = form.cleaned_data["email_notificaciones"].strip()
            activo = form.cleaned_data.get("activo", True)

            if conf is None:
                conf = ConfiguracionSistema(
                    clave=clave,
                    tipo="string",
                )

            conf.valor = email
            conf.activo = activo
            conf.save()

            messages.success(request, "Remitente de notificaciones actualizado")
            return redirect("configuracion_email_notificaciones")
    else:
        form = EmailNotificacionesForm(initial=initial)

    return render(request, 'config_email_notificaciones.html', {
        'form': form,
        'conf': conf,
    })


# ==================
# MANEJO DE ERRRORES
# ==================
def custom_permission_denied(request, exception=None):
    """Vista personalizada para errores 403 (Permiso denegado)"""
    return render(request, '403.html', status=403)

def custom_page_not_found(request, exception=None):
    """Vista personalizada para errores 404 (Página no encontrada)"""
    return render(request, '404.html', status=404)

def custom_server_error(request):
    """Vista personalizada para errores 500 (Error del servidor)"""
    return render(request, '500.html', status=500)

def csrf_failure(request, reason=""):
    """Vista personalizada para errores CSRF"""
    return render(request, '403_csrf.html', status=403)

