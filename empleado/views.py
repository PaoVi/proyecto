from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.db import IntegrityError
from django.db.models import Q

from seguridad.models import Usuario
from .models import Empleado
from .forms import EmpleadoAsignarUsuarioForm, EmpleadoForm, EmpleadoEditarForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.db.models import Q

@login_required
@permission_required('seguridad.agregar_empleados', raise_exception=True)
def empleado_crear(request):
    if request.method == 'POST':
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            try:
                emp = form.save()
                messages.success(request, f'Empleado {emp.nombre} registrado')
                return redirect('empleado_lista')
            except IntegrityError:
                form.add_error('cedula_ruc', 'Ya existe un empleado con este documento.')
    else:
        form = EmpleadoForm()

    return render(request, 'empleado/empleado_crear.html', {
        'form': form,
        'formulario': form, 
    })


@login_required
@permission_required('seguridad.ver_empleados', raise_exception=True)
def empleado_ver(request, empleado_id):
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    return render(request, 'empleado/empleado_ver.html', {
        'empleado': empleado,
    })


@login_required
@permission_required('seguridad.editar_empleados', raise_exception=True)
def empleado_editar(request, empleado_id):
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    puede_desactivar_empleados = request.user.has_perm('seguridad.desactivar_empleados')

    if request.method == 'POST':
        form = EmpleadoEditarForm(request.POST, instance=empleado)
        if form.is_valid():
            emp = form.save()
            messages.success(request,f'Empleado {emp.nombre} actualizado')
            return redirect('empleado_lista')
    else:
        form = EmpleadoEditarForm(instance=empleado)

    return render(request, 'empleado/empleado_editar.html', {
        'form': form,
        'empleado': empleado,
        'puede_desactivar_empleados': puede_desactivar_empleados,
    })


@login_required
@permission_required('seguridad.desactivar_empleados', raise_exception=True)
def empleado_desactivar(request, empleado_id):
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    empleado.estado = not empleado.estado
    empleado.save()
    estado_txt = 'activado' if empleado.estado else 'desactivado'
    messages.success(request, f'Empleado {empleado.nombre} {estado_txt}')
    return redirect('empleado_lista')


@login_required
@permission_required('seguridad.ver_empleados', raise_exception=True)
def empleado_lista(request):
    nombre = (request.GET.get('nombre') or '').strip()
    cedula_ruc = (request.GET.get('cedula_ruc') or '').strip()  
    cargo = (request.GET.get('cargo') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    qs = Empleado.objects.all()

    if nombre:
        qs = qs.filter(nombre__icontains=nombre)

    if cedula_ruc:
        valor = cedula_ruc.replace(' ', '')
        qs = qs.filter(
            Q(cedula_ruc__icontains=valor) |
            Q(cedula_ruc__icontains=valor.replace('-', ''))
        )

    if cargo:
        qs = qs.filter(cargo__icontains=cargo)

    if estado == 'activo':
        qs = qs.filter(estado=True)
    elif estado == 'inactivo':
        qs = qs.filter(estado=False)

    qs = qs.order_by('nombre')

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    empleados = paginator.get_page(page_number)

    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()

    # OBTENER LISTA DE CARGOS EXISTENTES 
    cargos_qs = (Empleado.objects
                .exclude(cargo__isnull=True)
                .exclude(cargo__exact='')
                .values_list('cargo', flat=True)
                .distinct()
                .order_by('cargo'))
    cargos = [(c, c) for c in cargos_qs]

    return render(request, 'empleado/empleado_lista.html', {
        'empleados': empleados,
        'qs_no_page': qs_no_page,
        'cargos': cargos,
    })


# =====================
# VÍNCULOS DEL EMPLEADO
# =====================

@login_required
def buscar_usuarios_vincular(request):
    """Vista para autocompletar usuarios - SOLO USUARIOS SIN EMPLEADO"""
    query = request.GET.get('q', '').strip()
    contexto = request.GET.get('contexto', 'general')
    
    try:
        # Base query - usuarios activos del modelo Usuario (no User de Django)
        usuarios = Usuario.objects.filter(is_active=True)
        
        # FILTRAR POR CONTEXTO - para asignación, solo usuarios sin empleado
        if contexto == 'asignacion':
            # Excluir usuarios que YA tienen empleado asociado
            usuarios = usuarios.filter(empleado__isnull=True)
        
        # Aplicar filtro de búsqueda si hay query - SOLO por username
        if query:
            usuarios = usuarios.filter(username__icontains=query)
        
        # Ordenar y limitar resultados
        usuarios = usuarios.order_by('username')[:10]
        
        # Formatear respuesta
        usuarios_data = []
        for usuario in usuarios:
            nombre_completo = f"{usuario.first_name} {usuario.last_name}".strip()
            if not nombre_completo:
                nombre_completo = "Sin nombre completo"
                
            usuarios_data.append({
                'id': usuario.pk,
                'text': f"{usuario.username} - {usuario.email}",
                'username': usuario.username,
                'email': usuario.email,
                'nombre_completo': nombre_completo,
            })
        
        return JsonResponse(usuarios_data, safe=False)
        
    except Exception as e:
        print(f"Error en búsqueda de usuarios: {e}")
        return JsonResponse([], safe=False)
    


@login_required
@permission_required('seguridad.ver_empleados', raise_exception=True)
def empleado_usuario(request, empleado_id):
    """Vista para mostrar el usuario vinculado al empleado"""
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    
    return render(request, 'empleado/empleado_usuario.html', {
        'empleado': empleado,
    })


@login_required
@permission_required('seguridad.editar_empleados', raise_exception=True)
def empleado_asignar_usuario(request, empleado_id):
    empleado = get_object_or_404(Empleado, pk=empleado_id)

    if request.method == "POST":
        form = EmpleadoAsignarUsuarioForm(request.POST, empleado=empleado)
        if form.is_valid():

            form.save()
            user = form.cleaned_data["user"]
            
            messages.success(request, f"Usuario {user.username} vinculado")
            return redirect("empleado_ver", empleado.pk)
    else:
        form = EmpleadoAsignarUsuarioForm(empleado=empleado)

    return render(request, "empleado/empleado_asignar_usuario.html", {
        "empleado": empleado,
        "form": form,
    })


@login_required
@permission_required('seguridad.editar_empleados', raise_exception=True)
def empleado_eliminar_usuario(request, empleado_id):
    if request.method == "POST":
        empleado = get_object_or_404(Empleado, pk=empleado_id)
        
        if empleado.user:
            # Guardar información del usuario antes de eliminarlo
            usuario_nombre = empleado.user.username
            usuario_email = empleado.user.email
            usuario_telefono = empleado.user.telefono
            
            # Mantener los datos en el empleado antes de desvincular
            # Si el empleado no tiene email pero el usuario sí, mantenerlo en el empleado
            if not empleado.correo_electronico and usuario_email:
                empleado.correo_electronico = usuario_email
            
            # Si el empleado no tiene teléfono pero el usuario sí, mantenerlo en el empleado
            if not empleado.telefono and usuario_telefono:
                empleado.telefono = usuario_telefono
            
            # Guardar los cambios en el empleado primero
            empleado.save()
            
            # Ahora desvincular el usuario y limpiar sus datos
            usuario = empleado.user
            
            # Limpiar los datos del usuario (email y teléfono)
            usuario.email = ""
            usuario.telefono = ""
            
            # Guardar el usuario con datos limpios
            usuario.save()
            
            # Finalmente desvincular
            empleado.user = None
            empleado.save(update_fields=["user"])
            
            # FORZAR LA ACTUALIZACIÓN DE LA INSTANCIA DEL USUARIO EN LA SESIÓN
            # Si el usuario desvinculado es el mismo que está logueado, actualizar la sesión
            if request.user.pk == usuario.pk:
                from django.contrib.auth import update_session_auth_hash
                # Recargar el usuario desde la base de datos
                usuario_refreshed = Usuario.objects.get(pk=usuario.pk)
                update_session_auth_hash(request, usuario_refreshed)
            
            messages.success(request, f"Usuario {usuario_nombre} desvinculado")
        else:
            messages.info(request, "El empleado no tiene usuario vinculado")
        
        return redirect('empleado_usuario', empleado_id=empleado_id)
    return redirect('empleado_usuario', empleado_id=empleado_id)

