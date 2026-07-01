from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from cliente.models import Cliente
from presupuesto.models import Presupuesto
from .models import Vehiculo
from .forms import VehiculoForm, VehiculoEditarForm, VehiculoVincularClienteForm
from django.utils.translation import gettext_lazy as _


# =========
# VEHICULOS
# =========
@login_required
@permission_required('seguridad.agregar_vehiculos', raise_exception=True)
def vehiculo_crear(request):
    if request.method == "POST":
        form = VehiculoForm(request.POST)
        if form.is_valid():

            v = form.save()
            messages.success(
                request,
                _(f"Vehículo {v.marca} {v.modelo} registrado")
            )
            return redirect("vehiculo_lista")
    else:
        form = VehiculoForm()
    return render(request, "vehiculo/vehiculo_crear.html", {"form": form})


@login_required
@permission_required('seguridad.ver_vehiculos', raise_exception=True)
def vehiculo_ver(request, vehiculo_id):
    v = get_object_or_404(Vehiculo, pk=vehiculo_id)
    return render(request, "vehiculo/vehiculo_ver.html", {"vehiculo": v})


@login_required
@permission_required('seguridad.editar_vehiculos', raise_exception=True)
def vehiculo_editar(request, vehiculo_id):
    vehiculo = get_object_or_404(Vehiculo, pk=vehiculo_id)
    puede_desactivar_vehiculos = request.user.has_perm('seguridad.desactivar_vehiculos')

    if request.method == 'POST':
        form = VehiculoEditarForm(request.POST, instance=vehiculo)
        if form.is_valid():
            # Guardar solo los campos del formulario, NO propietario/poseedor
            vehiculo_actualizado = form.save(commit=False)
            # Mantener los valores existentes de propietario y poseedor
            vehiculo_actualizado.save()
            messages.success(request, f"Vehículo {vehiculo.marca} {vehiculo.modelo} actualizado")
            return redirect('vehiculo_lista')
    else:
        form = VehiculoEditarForm(instance=vehiculo)

    return render(request, 'vehiculo/vehiculo_editar.html', {
        'form': form,
        'vehiculo': vehiculo,
        'puede_desactivar_vehiculos': puede_desactivar_vehiculos,
    })


@login_required
@permission_required('seguridad.editar_vehiculos', raise_exception=True) 
def vehiculo_desactivar(request, vehiculo_id):
    if request.method != "POST":
        return redirect('vehiculo_lista')
    v = get_object_or_404(Vehiculo, pk=vehiculo_id)
    v.estado = not v.estado
    v.save(update_fields=["estado"])
    messages.success(request, f"Vehículo {v.marca} {v.modelo} {'activado' if v.estado else 'desactivado'}")
    return redirect('vehiculo_lista')


@login_required
@permission_required('seguridad.ver_vehiculos', raise_exception=True)
def vehiculo_lista(request):
    q      = (request.GET.get('q') or '').strip()
    marca  = (request.GET.get('marca') or '').strip()
    modelo = (request.GET.get('modelo') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    qs = Vehiculo.objects.all()

    if q:
        qs = qs.filter(
            Q(nro_chapa__icontains=q) |
            Q(nro_chasis__icontains=q) |
            Q(color__icontains=q)
        )
    if marca:
        qs = qs.filter(marca__icontains=marca)
    if modelo:
        qs = qs.filter(modelo__icontains=modelo)
    if estado == 'activo':
        qs = qs.filter(estado=True)
    elif estado == 'inactivo':
        qs = qs.filter(estado=False)

    qs = qs.order_by('-fecha_registro')

    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    vehiculos = paginator.get_page(page)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    return render(request, 'vehiculo/vehiculo_lista.html', {
        'vehiculos': vehiculos,
        'q': q,
        'marca': marca,
        'modelo': modelo,
        'estado': estado,
        'qs_no_page': qs_no_page,  
    })
 

# =====================
# VÍNCULOS DEL VEHÍCULO
# =====================
@login_required
def buscar_clientes_vincular(request):
    """Vista para autocompletar clientes"""
    query = request.GET.get('q', '')
    
    try:     
        if query:
            # Buscar por docuemento o nombre
            clientes = Cliente.objects.filter(
                Q(numero_documento__icontains=query) |
                Q(nombre__icontains=query)
            ).filter(is_active=True)[:10]
        else:
            # Si no hay query, devolver todos los clientes (limitado)
            clientes = Cliente.objects.filter(is_active=True)[:10]
        
        clientes_data = []
        for cliente in clientes:
            clientes_data.append({
                'id': cliente.id,
                'text': f"{cliente.numero_documento} - {cliente.nombre}",
                'documento': cliente.numero_documento or '',
                'nombre': cliente.nombre or '',
                'telefono': cliente.telefono or ''
            })
        
        return JsonResponse(clientes_data, safe=False)
    
    except Exception as e:
        # En caso de error, devolver array vacío
        return JsonResponse([], safe=False)


@login_required
@permission_required('seguridad.ver_vehiculos', raise_exception=True)
def vehiculo_propietarios(request, vehiculo_id):
    vehiculo = get_object_or_404(Vehiculo, pk=vehiculo_id)
    
    return render(request, "vehiculo/vehiculo_propietarios.html", {
        "vehiculo": vehiculo,
    })


@login_required
@permission_required('seguridad.editar_vehiculos', raise_exception=True)
def vehiculo_vincular_cliente(request, vehiculo_id):
    vehiculo = get_object_or_404(Vehiculo, pk=vehiculo_id)
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == "POST":
        form = VehiculoVincularClienteForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            cliente = form.cleaned_data["cliente"]
            tipo_vinculacion = request.POST.get("tipo_vinculacion", "propietario")

            # Validaciones según el tipo de vinculación - EVITAR SOBREESCRIBIR
            mensaje_error = None
            
            if tipo_vinculacion == 'propietario':
                # Verificar si el vehículo YA TIENE un propietario DIFERENTE
                if vehiculo.propietario and vehiculo.propietario.id != cliente.id:
                    mensaje_error = f'El vehículo ya tiene otro PROPIETARIO asignado: {vehiculo.propietario.nombre}'
            
            elif tipo_vinculacion == 'poseedor':
                # Verificar si el vehículo YA TIENE un poseedor DIFERENTE
                if vehiculo.poseedor and vehiculo.poseedor.id != cliente.id:
                    mensaje_error = f'El vehículo ya tiene otro POSEEDOR asignado: {vehiculo.poseedor.nombre}'
            
            elif tipo_vinculacion == 'ambos':
                # Verificar propietario
                if vehiculo.propietario and vehiculo.propietario.id != cliente.id:
                    mensaje_error = f'El vehículo ya tiene otro PROPIETARIO asignado: {vehiculo.propietario.nombre}'
                # Verificar poseedor (solo si no hay error anterior)
                elif vehiculo.poseedor and vehiculo.poseedor.id != cliente.id:
                    mensaje_error = f'El vehículo ya tiene otro POSEEDOR asignado: {vehiculo.poseedor.nombre}'

            # Si hay error, mostrar mensaje y volver al formulario
            if mensaje_error:
                messages.error(request, mensaje_error)
                return render(request, "vehiculo/vehiculo_vincular_cliente.html", {
                    "vehiculo": vehiculo, "form": form, "next": next_url
                })
            
            # Realizar la vinculación según el tipo
            if tipo_vinculacion == "propietario":
                vehiculo.propietario = cliente
                vehiculo.save(update_fields=["propietario"])
                messages.success(request, f"PROPIETARIO {cliente.nombre} vinculado")
            
            elif tipo_vinculacion == "poseedor":
                vehiculo.poseedor = cliente
                vehiculo.save(update_fields=["poseedor"])
                messages.success(request, f"POSEEDOR {cliente.nombre} vinculado")
            
            elif tipo_vinculacion == "ambos":
                vehiculo.propietario = cliente
                vehiculo.poseedor = cliente
                vehiculo.save(update_fields=["propietario", "poseedor"])
                messages.success(request, f"Cliente {cliente.nombre} vinculado como PROPIETARIO y POSEEDOR")

            return redirect(next_url) if next_url else redirect("vehiculo_propietarios", vehiculo.pk)
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = VehiculoVincularClienteForm(vehiculo=vehiculo)

    return render(
        request,
        "vehiculo/vehiculo_vincular_cliente.html",
        {"vehiculo": vehiculo, "form": form, "next": next_url},
    )


@login_required
@permission_required('seguridad.editar_vehiculos', raise_exception=True)
def vehiculo_eliminar_cliente(request, vehiculo_id):
    if request.method == "POST":
        vehiculo = get_object_or_404(Vehiculo, pk=vehiculo_id)
        tipo_vinculacion = request.POST.get("tipo_vinculacion", "propietario")
        
        # Obtener información del cliente antes de eliminar
        cliente_nombre = ""
        mensaje = ""
        
        if tipo_vinculacion == "propietario":
            if vehiculo.propietario:
                cliente_nombre = vehiculo.propietario.nombre
                vehiculo.propietario = None
                vehiculo.save(update_fields=["propietario"])
                mensaje = f"PROPIETARIO {cliente_nombre} eliminado"
            else:
                messages.info(request, "El vehículo no tiene propietario asignado")
                return redirect('vehiculo_propietarios', vehiculo_id=vehiculo_id)
                
        elif tipo_vinculacion == "poseedor":
            if vehiculo.poseedor:
                cliente_nombre = vehiculo.poseedor.nombre
                vehiculo.poseedor = None
                vehiculo.save(update_fields=["poseedor"])
                mensaje = f"POSEEDOR {cliente_nombre} eliminado"
            else:
                messages.info(request, "El vehículo no tiene poseedor asignado")
                return redirect('vehiculo_propietarios', vehiculo_id=vehiculo_id)
                
        elif tipo_vinculacion == "ambos":
            propietario_nombre = vehiculo.propietario.nombre if vehiculo.propietario else ""
            poseedor_nombre = vehiculo.poseedor.nombre if vehiculo.poseedor else ""
            
            if vehiculo.propietario and vehiculo.poseedor:
                # Ambos roles asignados al mismo cliente
                if vehiculo.propietario.id == vehiculo.poseedor.id:
                    cliente_nombre = vehiculo.propietario.nombre
                    vehiculo.propietario = None
                    vehiculo.poseedor = None
                    vehiculo.save(update_fields=["propietario", "poseedor"])
                    mensaje = f"Cliente {cliente_nombre} eliminado como PROPIETARIO Y POSEEDOR"
                else:
                    # Diferentes clientes en cada rol
                    vehiculo.propietario = None
                    vehiculo.poseedor = None
                    vehiculo.save(update_fields=["propietario", "poseedor"])
                    mensaje = f"PROPIETARIO {propietario_nombre} y POSEEDOR {poseedor_nombre} eliminados"
            elif vehiculo.propietario:
                # Solo propietario asignado
                vehiculo.propietario = None
                vehiculo.save(update_fields=["propietario"])
                mensaje = f"PROPIETARIO {propietario_nombre} eliminado"
            elif vehiculo.poseedor:
                # Solo poseedor asignado
                vehiculo.poseedor = None
                vehiculo.save(update_fields=["poseedor"])
                mensaje = f"POSEEDOR {poseedor_nombre} eliminado"
            else:
                messages.info(request, "El vehículo no tiene propietario ni poseedor asignado")
                return redirect('vehiculo_propietarios', vehiculo_id=vehiculo_id)
        
        messages.success(request, mensaje)
        return redirect('vehiculo_propietarios', vehiculo_id=vehiculo_id)
    
    return redirect('vehiculo_propietarios', vehiculo_id=vehiculo_id)


@login_required
@permission_required('seguridad.ver_vehiculos', raise_exception=True)
def vehiculo_presupuestos(request, vehiculo_id):
    """Vista para mostrar presupuestos del vehículo"""
    vehiculo = get_object_or_404(Vehiculo, pk=vehiculo_id)
    
    # Obtener presupuestos del vehículo
    presupuestos = Presupuesto.objects.filter(vehiculo=vehiculo).order_by('-fecha_creacion')
    
    context = {
        'vehiculo': vehiculo,
        'presupuestos': presupuestos,
        'total_presupuestos': presupuestos.count(),
        'presupuestos_pendientes': presupuestos.filter(estado='pendiente').count(),
        'presupuestos_aprobados': presupuestos.filter(estado='aprobado').count(),
        'presupuestos_rechazados': presupuestos.filter(estado='rechazado').count(),
    }
    return render(request, 'vehiculo/vehiculo_presupuestos.html', context)


# ##############
# ENTRADA/SALIDA
# ##############
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q

@login_required
@permission_required('seguridad.ver_vehiculos', raise_exception=True)
def vehiculo_ingreso_lista(request):
    """Vista provisional para el control de ingreso vehicular"""
    
    # Parámetros de filtro (provisionales)
    chapa_query = request.GET.get('chapa', '').strip()
    cliente_query = request.GET.get('cliente', '').strip()
    estado_ingreso_query = request.GET.get('estado_ingreso', '')
    fecha_ingreso_query = request.GET.get('fecha_ingreso', '')
    
    # DATOS DE PRUEBA - ESTO SE REEMPLAZARÁ CON TU MODELO REAL
    vehiculos_prueba = [
        {
            'id': 1,
            'chapa': 'ABC-123',
            'marca': 'Toyota',
            'modelo': 'Corolla 2023',
            'cliente_nombre': 'Juan Pérez',
            'cliente_documento': '1234567',
            'cliente_telefono': '0981123456',
            'presupuesto_numero': 'P-001',
            'presupuesto_estado': 'pendiente',
            'orden_trabajo_numero': 'OT-001',
            'orden_trabajo_estado': 'en_proceso',
            'fecha_ingreso': '2025-01-15',
            'estado_ingreso': 'en_taller',
            'fecha_salida': None,
        },
        {
            'id': 2,
            'chapa': 'DEF-456',
            'marca': 'Ford',
            'modelo': 'Ranger 2022',
            'cliente_nombre': 'María González',
            'cliente_documento': '7654321',
            'cliente_telefono': '0982654321',
            'presupuesto_numero': 'P-002',
            'presupuesto_estado': 'aprobado',
            'orden_trabajo_numero': 'OT-002',
            'orden_trabajo_estado': 'completada',
            'fecha_ingreso': '2025-01-14',
            'estado_ingreso': 'esperando_repuesto',
            'fecha_salida': None,
        },
        {
            'id': 3,
            'chapa': 'GHI-789',
            'marca': 'Chevrolet',
            'modelo': 'Onix 2024',
            'cliente_nombre': 'Carlos López',
            'cliente_documento': '4567890',
            'cliente_telefono': '0983456789',
            'presupuesto_numero': 'P-003',
            'presupuesto_estado': 'rechazado',
            'orden_trabajo_numero': 'OT-003',
            'orden_trabajo_estado': 'pendiente',
            'fecha_ingreso': '2025-01-13',
            'estado_ingreso': 'en_reparacion',
            'fecha_salida': None,
        },
        {
            'id': 4,
            'chapa': 'JKL-012',
            'marca': 'Honda',
            'modelo': 'Civic 2023',
            'cliente_nombre': 'Ana Martínez',
            'cliente_documento': '9876543',
            'cliente_telefono': '0984987654',
            'presupuesto_numero': 'P-004',
            'presupuesto_estado': 'aprobado',
            'orden_trabajo_numero': 'OT-004',
            'orden_trabajo_estado': 'completada',
            'fecha_ingreso': '2025-01-10',
            'estado_ingreso': 'salio',
            'fecha_salida': '2025-01-16',
        },
    ]
    
    # Aplicar filtros básicos (provisional)
    vehiculos_filtrados = vehiculos_prueba
    
    if chapa_query:
        vehiculos_filtrados = [v for v in vehiculos_filtrados if chapa_query.lower() in v['chapa'].lower()]
    
    if cliente_query:
        vehiculos_filtrados = [v for v in vehiculos_filtrados if cliente_query.lower() in v['cliente_nombre'].lower()]
    
    if estado_ingreso_query:
        vehiculos_filtrados = [v for v in vehiculos_filtrados if v['estado_ingreso'] == estado_ingreso_query]
    
    # Estadísticas (provisionales)
    estadisticas = {
        'ingresos_semana': len([v for v in vehiculos_prueba if v['fecha_ingreso'] >= '2025-01-13']),  # Esta semana
        'en_reparacion': len([v for v in vehiculos_prueba if v['estado_ingreso'] == 'en_reparacion']),
        'anteriores': len([v for v in vehiculos_prueba if v['fecha_ingreso'] < '2025-01-13']),  # Semanas anteriores
        'total_taller': len([v for v in vehiculos_prueba if not v['fecha_salida']]),  # Sin fecha de salida
    }
    
    # Paginación (provisional)
    paginator = Paginator(vehiculos_filtrados, 10)
    page_number = request.GET.get('page')
    vehiculos_paginados = paginator.get_page(page_number)
    
    # Mantener parámetros GET para paginación
    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()
    
    context = {
        'vehiculos': vehiculos_paginados,
        'estadisticas': estadisticas,
        'qs_no_page': qs_no_page,
        'filtros_actuales': {
            'chapa': chapa_query,
            'cliente': cliente_query,
            'estado_ingreso': estado_ingreso_query,
            'fecha_ingreso': fecha_ingreso_query,
        }
    }
    
    return render(request, 'vehiculo/vehiculo_ingreso_lista.html', context)

@login_required
@permission_required('seguridad.agregar_vehiculos', raise_exception=True)
def vehiculo_ingreso_crear(request):
    """Vista provisional para crear nuevo ingreso vehicular"""
    
    # Esta es una vista temporal - redirige a la lista por ahora
    from django.shortcuts import redirect
    from django.contrib import messages
    
    messages.info(request, "Función de crear nuevo ingreso en desarrollo")
    return redirect('vehiculo_ingreso_lista')