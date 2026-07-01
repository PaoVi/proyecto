from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404, redirect, render
from .forms import ProveedorForm, ProveedorEditarForm
from .models import Proveedor


# ============
# PROVEEDORES
# ============

@login_required
@permission_required('seguridad.agregar_proveedores', raise_exception=True)
def proveedor_crear(request):
    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    p = form.save()
                messages.success(request, f"Proveedor {p.razon_social} creado")
                return redirect("proveedor_lista")

            except DjangoValidationError as e:
                # Si vienen errores por campo
                if hasattr(e, "message_dict"):
                    for field, msgs in e.message_dict.items():
                        for msg in msgs:
                            if field in form.fields:
                                form.add_error(field, msg)
                            else:
                                form.add_error(None, msg)
                else:
                    # Errores no mapeados a campos
                    for msg in e.messages:
                        form.add_error(None, msg)

            except IntegrityError:
                # Clave única duplicada (ej. RUC)
                form.add_error("ruc", "Ya existe un proveedor con ese RUC.")
    else:
        form = ProveedorForm()

    return render(request, "proveedor/proveedor_crear.html", {"form": form})


@login_required
@permission_required('seguridad.ver_proveedores', raise_exception=True)
def proveedor_ver(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    return render(request, "proveedor/proveedor_ver.html", {"p": proveedor})


@login_required
@permission_required('seguridad.editar_proveedores', raise_exception=True)
def proveedor_editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    puede_desactivar_proveedores = request.user.has_perm('seguridad.desactivar_proveedores')

    if request.method == "POST":
        form = ProveedorEditarForm(request.POST, instance=proveedor)
        if form.is_valid():
            try:
                with transaction.atomic():
                    p = form.save()
                messages.success(request, f"Proveedor {p.razon_social} actualizado")
                return redirect(proveedor_lista)

            except DjangoValidationError as e:
                if hasattr(e, "message_dict"):
                    for field, msgs in e.message_dict.items():
                        for msg in msgs:
                            if field in form.fields:
                                form.add_error(field, msg)
                            else:
                                form.add_error(None, msg)
                else:
                    for msg in e.messages:
                        form.add_error(None, msg)

            except IntegrityError:
                form.add_error("ruc", "Ya existe un proveedor con ese RUC.")
    else:
        form = ProveedorEditarForm(instance=proveedor)

    return render(request, "proveedor/proveedor_editar.html", {
        "form": form,
        "p": proveedor,
        "puede_desactivar_proveedores": puede_desactivar_proveedores,
    })


@login_required
@permission_required('seguridad.desactivar_proveedores', raise_exception=True)
def proveedor_desactivar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    proveedor.is_active = not proveedor.is_active
    proveedor.save(update_fields=["is_active"])
    estado = "activado" if proveedor.is_active else "desactivado"
    messages.success(request, f"Proveedor {proveedor.razon_social} {estado}")
    return redirect(proveedor_lista)


@login_required
@permission_required('seguridad.ver_proveedores', raise_exception=True)
def proveedor_lista(request):
    ruc    = (request.GET.get("ruc") or "").strip()
    razon  = (request.GET.get("razon") or "").strip()
    estado = (request.GET.get("estado") or "").strip()

    qs = Proveedor.objects.all()

    if ruc:
        qs = qs.filter(ruc__icontains=ruc)
    if razon:
        qs = qs.filter(razon_social__icontains=razon)
    if estado == "activo":
        qs = qs.filter(is_active=True)
    elif estado == "inactivo":
        qs = qs.filter(is_active=False)

    qs = qs.order_by("razon_social")

    # PAGINACIÓN
    paginator = Paginator(qs, 10)
    page = request.GET.get("page")
    proveedores = paginator.get_page(page)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    return render(
        request,
        "proveedor/proveedor_lista.html",
        {
            "proveedores": proveedores,
            "f_ruc": ruc,
            "f_razon": razon,
            "f_estado": estado,
            "qs_no_page": qs_no_page,
        },
    )

