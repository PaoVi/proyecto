from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Sucursal


@login_required
@permission_required('sucursal.view_sucursal', raise_exception=True)
def sucursal_list(request):
    sucursales = Sucursal.objects.all()
    return render(request, 'sucursal/sucursal_list.html', {'sucursales': sucursales})


@login_required
@permission_required('sucursal.add_sucursal', raise_exception=True)
def sucursal_create(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        establecimiento = request.POST.get('establecimiento', '001').strip()
        punto_emision = request.POST.get('punto_emision', '001').strip()
        if nombre:
            Sucursal.objects.create(
                nombre=nombre,
                direccion=direccion,
                telefono=telefono,
                establecimiento=establecimiento,
                punto_emision=punto_emision,
            )
            messages.success(request, f"Sucursal '{nombre}' creada.")
            return redirect('sucursal:sucursal_list')
        messages.error(request, "El nombre es obligatorio.")
    return render(request, 'sucursal/sucursal_form.html', {'accion': 'Nueva'})


@login_required
@permission_required('sucursal.change_sucursal', raise_exception=True)
def sucursal_update(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        establecimiento = request.POST.get('establecimiento', '001').strip()
        punto_emision = request.POST.get('punto_emision', '001').strip()
        if nombre:
            sucursal.nombre = nombre
            sucursal.direccion = direccion
            sucursal.telefono = telefono
            sucursal.establecimiento = establecimiento
            sucursal.punto_emision = punto_emision
            sucursal.save()
            messages.success(request, "Sucursal actualizada.")
            return redirect('sucursal:sucursal_list')
        messages.error(request, "El nombre es obligatorio.")
    return render(request, 'sucursal/sucursal_form.html', {'sucursal': sucursal, 'accion': 'Editar'})


@login_required
def set_sucursal(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk, activo=True)
    perfil = getattr(request.user, 'perfil', None)
    if perfil:
        if perfil.sucursales_permitidas.filter(pk=pk).exists() or request.user.is_superuser:
            perfil.sucursal_activa = sucursal
            perfil.save(update_fields=['sucursal_activa'])
            messages.success(request, f"Sucursal cambiada a: {sucursal.nombre}")
        else:
            messages.error(request, "No tienes acceso a esa sucursal.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
@permission_required('sucursal.change_sucursal', raise_exception=True)
def sucursal_toggle(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    sucursal.activo = not sucursal.activo
    sucursal.save(update_fields=['activo'])
    estado = "activada" if sucursal.activo else "desactivada"
    messages.success(request, f"Sucursal '{sucursal.nombre}' {estado}.")
    return redirect('sucursal:sucursal_list')
