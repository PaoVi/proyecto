from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError as ModelValidationError 
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from presupuesto.models import Presupuesto
from .forms import ClienteForm, ClienteEditarForm, ClienteVincularVehiculoForm 
from .models import Cliente
from vehiculo.models import Vehiculo 
from django.db.models import Q


# ========
# CLIENTES
# ========

@login_required 
@permission_required('seguridad.agregar_clientes', raise_exception=True)
def cliente_crear(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    cliente = form.save()
                messages.success(
                    request,
                    f"Cliente {cliente.nombre} registrado"
                )
                return redirect("cliente_lista")

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
                form.add_error("numero_documento",
                               "Ya existe un cliente con ese número de documento.")

    else:
        form = ClienteForm()

    return render(request, "cliente/cliente_crear.html", {"form": form})


@login_required
@permission_required('seguridad.ver_clientes', raise_exception=True)
def cliente_ver(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    
    # Obtener vehículos donde el cliente es propietario
    vehiculos_propietario = cliente.vehiculo_set.all()
    
    # Obtener vehículos donde el cliente es poseedor (si usas related_name)
    vehiculos_poseedor = cliente.vehiculos_poseedor.all()
    
    # Combinar ambos querysets (eliminando duplicados si un vehículo aparece en ambos)
    vehiculos = (vehiculos_propietario | vehiculos_poseedor).distinct()
    
    return render(request, "cliente/cliente_ver.html", {
        "cliente": cliente,
        "vehiculos": vehiculos,
        "vehiculos_propietario": vehiculos_propietario,
        "vehiculos_poseedor": vehiculos_poseedor,
    })


@login_required
@permission_required('seguridad.editar_clientes', raise_exception=True)
def cliente_editar(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    puede_desactivar_clientes = request.user.has_perm('seguridad.desactivar_clientes')

    # Obtener vehículos donde el cliente es propietario
    vehiculos_propietario = Vehiculo.objects.filter(propietario=cliente).order_by('marca','modelo','nro_chapa')
    
    # Obtener vehículos donde el cliente es poseedor
    vehiculos_poseedor = Vehiculo.objects.filter(poseedor=cliente).order_by('marca','modelo','nro_chapa')
    
    # Combinar ambos querysets (eliminando duplicados)
    vehiculos = (vehiculos_propietario | vehiculos_poseedor).distinct()

    if request.method == "POST":
        form = ClienteEditarForm(request.POST, instance=cliente)
        if form.is_valid():
            try:
                form.save() 
                messages.success(request, f"Cliente {cliente.nombre} actualizado")
                return redirect("cliente_lista")
            except ModelValidationError as e:
                for field, msgs in e.message_dict.items():
                    for msg in msgs:
                        if field in form.fields:
                            form.add_error(field, msg)
                        else:
                            form.add_error(None, msg)
    else:
        form = ClienteEditarForm(instance=cliente)

    return render(
        request,
        "cliente/cliente_editar.html",
        {
            'form': form,
            'cliente': cliente,
            'puede_desactivar_clientes': puede_desactivar_clientes,
            'vehiculos': vehiculos,
            'vehiculos_propietario': vehiculos_propietario,
            'vehiculos_poseedor': vehiculos_poseedor,
        }
    )


@login_required
@permission_required('seguridad.desactivar_clientes', raise_exception=True)
def cliente_desactivar(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    cliente.is_active = not cliente.is_active
    cliente.save()
    estado = 'activado' if cliente.is_active else 'desactivado'
    messages.success(request, f'Cliente {cliente.nombre} {estado}')
    
    # Conservar todos los parámetros GET actuales
    get_params = request.GET.copy()
    
    # Construir URL manteniendo todos los parámetros
    base_url = reverse('cliente_lista')
    if get_params:
        return redirect(f"{base_url}?{get_params.urlencode()}")
    else:
        return redirect(base_url)


@login_required
@permission_required('seguridad.ver_clientes', raise_exception=True)
def cliente_lista(request):
    doc_query = request.GET.get('doc', '').strip()
    nombre_query = request.GET.get('nombre', '').strip()
    estado_query = request.GET.get('estado')
    tipo_cliente_query = request.GET.get('tipo_cliente')

    clientes = Cliente.objects.all()

    if doc_query:
        clientes = clientes.filter(numero_documento__icontains=doc_query)
    if nombre_query:
        clientes = clientes.filter(nombre__icontains=nombre_query)
    if estado_query == 'activo':
        clientes = clientes.filter(is_active=True)
    elif estado_query == 'inactivo':
        clientes = clientes.filter(is_active=False)
    if tipo_cliente_query in ['fisica', 'juridica']:
        clientes = clientes.filter(tipo_cliente=tipo_cliente_query)

    # ORDENAR ALFABÉTICAMENTE POR NOMBRE Y APELLIDO
    clientes = clientes.order_by('nombre', 'numero_documento')

    # PAGINACIÓN - 10 elementos por página
    paginator = Paginator(clientes, 10)
    page_number = request.GET.get('page')
    clientes = paginator.get_page(page_number) 

    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()

    return render(request, 'cliente/cliente_lista.html', {
        'clientes': clientes,
        'qs_no_page': qs_no_page,
    })


# ====================
# VÍNCULOS DEL CLIENTE
# ====================

@login_required
def buscar_vehiculos_vincular(request):
    """Vista ESPECÍFICA para autocompletar vehículos para VINCULACIÓN"""
    query = request.GET.get('q', '').strip()
    
    try:
        # TODOS los vehículos ACTIVOS
        vehiculos = Vehiculo.objects.filter(estado=True)
        
        # Aplicar filtro de búsqueda si hay query
        if query:
            vehiculos = vehiculos.filter(
                Q(nro_chapa__icontains=query) |
                Q(nro_chasis__icontains=query) |
                Q(marca__icontains=query) |
                Q(modelo__icontains=query)
            )
        
        # Ordenar y limitar resultados
        vehiculos = vehiculos.order_by('nro_chapa')[:10]
        
        # Formatear respuesta con información de disponibilidad
        vehiculos_data = []
        for vehiculo in vehiculos:
            disponible_propietario = vehiculo.propietario is None
            disponible_poseedor = vehiculo.poseedor is None
            
            vehiculos_data.append({
                'id': vehiculo.pk,
                'text': f"{vehiculo.nro_chapa} - {vehiculo.marca} {vehiculo.modelo}",
                'chapa': vehiculo.nro_chapa or 'Sin chapa',
                'chasis': vehiculo.nro_chasis or 'Sin chasis',
                'marca': vehiculo.marca or 'Sin marca',
                'modelo': vehiculo.modelo or 'Sin modelo',
                'disponible_propietario': disponible_propietario,
                'disponible_poseedor': disponible_poseedor,
                'propietario_actual': vehiculo.propietario_id,
                'poseedor_actual': vehiculo.poseedor_id,
            })
        
        return JsonResponse(vehiculos_data, safe=False)
        
    except Exception as e:
        print(f"DEBUG: Error en búsqueda: {e}")
        return JsonResponse([], safe=False)


@login_required
@permission_required('seguridad.ver_clientes', raise_exception=True)
def cliente_vehiculos(request, cliente_id):
    """Vista para mostrar vehículos vinculados al cliente"""
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    
    # Obtener parámetros de búsqueda
    q = request.GET.get('q', '').strip()
    estado_query = request.GET.get('estado', 'todos')
    
    # Obtener vehículos donde el cliente es propietario o poseedor
    vehiculos_propietario = Vehiculo.objects.filter(propietario=cliente)
    vehiculos_poseedor = Vehiculo.objects.filter(poseedor=cliente)
    
    # Combinar ambos querysets (eliminando duplicados)
    vehiculos = (vehiculos_propietario | vehiculos_poseedor).distinct()
    
    # Aplicar filtros
    if q:
        vehiculos = vehiculos.filter(
            Q(nro_chapa__icontains=q) |
            Q(nro_chasis__icontains=q) |
            Q(marca__icontains=q) |
            Q(modelo__icontains=q)
        )
    
    if estado_query == 'activo':
        vehiculos = vehiculos.filter(estado=True)
    elif estado_query == 'inactivo':
        vehiculos = vehiculos.filter(estado=False)
    
    # Ordenar resultados
    vehiculos = vehiculos.order_by('marca', 'modelo')
    
    # PAGINACIÓN
    paginator = Paginator(vehiculos, 10)
    page_number = request.GET.get('page')
    vehiculos_paginados = paginator.get_page(page_number)
    
    # Mantener parámetros GET para paginación
    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()
    
    context = {
        'cliente': cliente,
        'vehiculos': vehiculos_paginados,
        'total_vehiculos': vehiculos.count(),
        'vehiculos_propietario': vehiculos_propietario.count(),
        'vehiculos_poseedor': vehiculos_poseedor.count(),
        'qs_no_page': qs_no_page,
        'filtro_actual': estado_query,
        'busqueda_actual': q,
    }
    return render(request, 'cliente/cliente_vehiculos.html', context)



@login_required
@permission_required('seguridad.editar_clientes', raise_exception=True)
def cliente_vincular_vehiculo(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == "POST":
        
        form = ClienteVincularVehiculoForm(request.POST, cliente=cliente)
        if form.is_valid():
            print("DEBUG: Form es válido")
            vehiculo = form.cleaned_data["vehiculo"]
            tipo_vinculacion = request.POST.get('tipo_vinculacion', 'propietario')
            
            # Validaciones según el tipo de vinculación
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
                return render(request, "cliente/cliente_vincular_vehiculo.html", {
                    "cliente": cliente, "form": form, "next": next_url
                })
            
            # Realizar la vinculación según el tipo
            if tipo_vinculacion == 'propietario':
                # Solo vincular como propietario (no modificar poseedor)
                vehiculo.propietario = cliente
                vehiculo.save(update_fields=["propietario"])
                messages.success(request, f"Vehículo {vehiculo.marca} {vehiculo.modelo} vinculado como PROPIETARIO")
            
            elif tipo_vinculacion == 'poseedor':
                # Solo vincular como poseedor (no modificar propietario)
                vehiculo.poseedor = cliente
                vehiculo.save(update_fields=["poseedor"])
                messages.success(request, f"Vehículo {vehiculo.marca} {vehiculo.modelo} vinculado como POSEEDOR")
            
            elif tipo_vinculacion == 'ambos':
                # Vincular como ambos roles
                vehiculo.propietario = cliente
                vehiculo.poseedor = cliente
                vehiculo.save(update_fields=["propietario", "poseedor"])
                messages.success(request, f"Vehículo {vehiculo.marca} {vehiculo.modelo} vinculado como PROPIETARIO Y POSEEDOR")
            
            return redirect(next_url) if next_url else redirect("cliente_vehiculos", cliente.pk)
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ClienteVincularVehiculoForm(cliente=cliente)

    return render(
        request,
        "cliente/cliente_vincular_vehiculo.html",
        {
            "cliente": cliente,
            "form": form,
            "next": next_url,
        },
    )


@login_required
@permission_required('seguridad.editar_clientes', raise_exception=True)
def cliente_eliminar_vehiculo(request, cliente_id, vehiculo_id):
    
    if request.method == "POST":
        try:
            # Buscar cliente
            cliente = Cliente.objects.get(pk=cliente_id)
            vehiculo = Vehiculo.objects.get(pk=vehiculo_id)
            
            # Determinar el tipo de vinculación actual
            es_propietario = vehiculo.propietario_id == cliente.pk
            es_poseedor = vehiculo.poseedor_id == cliente.pk
            
            
            if not es_propietario and not es_poseedor:
                messages.error(request, "El vehículo no está vinculado a este cliente")
                return redirect('cliente_vehiculos', cliente_id=cliente_id)
            
            # Obtener el tipo de desvinculación del formulario
            tipo_desvinculacion = request.POST.get('tipo_desvinculacion', 'ambos')
            
            # Realizar la desvinculación según el tipo seleccionado
            campos_actualizados = []
            mensaje_exito = ""
            
            if tipo_desvinculacion == 'propietario' and es_propietario:
                vehiculo.propietario = None
                campos_actualizados.append("propietario")
                mensaje_exito = f"Vehículo {vehiculo.marca} {vehiculo.modelo} desvinculado como PROPIETARIO"
                
            elif tipo_desvinculacion == 'poseedor' and es_poseedor:
                vehiculo.poseedor = None
                campos_actualizados.append("poseedor")
                mensaje_exito = f"Vehículo {vehiculo.marca} {vehiculo.modelo} desvinculado como POSEEDOR"
                
            elif tipo_desvinculacion == 'ambos':
                if es_propietario:
                    vehiculo.propietario = None
                    campos_actualizados.append("propietario")
                if es_poseedor:
                    vehiculo.poseedor = None
                    campos_actualizados.append("poseedor")
                
                if es_propietario and es_poseedor:
                    mensaje_exito = f"Vehículo {vehiculo.marca} {vehiculo.modelo} desvinculado (PROPIETARIO Y POSEEDOR)"
                elif es_propietario:
                    mensaje_exito = f"Vehículo {vehiculo.marca} {vehiculo.modelo} desvinculado como PROPIETARIO"
                elif es_poseedor:
                    mensaje_exito = f"Vehículo {vehiculo.marca} {vehiculo.modelo} desvinculado como POSEEDOR"
            
            # Guardar cambios si hay campos para actualizar
            if campos_actualizados:
                vehiculo.save(update_fields=campos_actualizados)
                messages.success(request, mensaje_exito)
            else:
                messages.warning(request, "No se realizaron cambios en la vinculación")
            
            return redirect('cliente_vehiculos', cliente_id=cliente_id)
            
        except Cliente.DoesNotExist:
            clientes_existentes = Cliente.objects.all().values_list('pk', flat=True)
            messages.error(request, f"El cliente con ID {cliente_id} no existe")
            return redirect('cliente_lista')
            
        except Vehiculo.DoesNotExist:
            vehiculos_existentes = Vehiculo.objects.all().values_list('pk', flat=True)
            messages.error(request, f"El vehículo con ID {vehiculo_id} no existe")
            return redirect('cliente_vehiculos', cliente_id=cliente_id)
            
        except Exception as e:
            # Debug adicional para ver qué tiene el objeto vehiculo
            try:
                vehiculo = Vehiculo.objects.get(pk=vehiculo_id)
            except:
                pass
            messages.error(request, f"Error inesperado: {str(e)}")
            return redirect('cliente_vehiculos', cliente_id=cliente_id)
    
    # Si no es POST, redirigir a la página de vehículos
    return redirect('cliente_vehiculos', cliente_id=cliente_id)


@login_required
@permission_required('seguridad.ver_clientes', raise_exception=True)
def cliente_presupuestos(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    
    # Obtener presupuestos del cliente
    presupuestos = Presupuesto.objects.filter(cliente=cliente)
    
    context = {
        'cliente': cliente,
        'presupuestos': presupuestos,
        'total_presupuestos': presupuestos.count(),
        'presupuestos_pendientes': presupuestos.filter(estado='pendiente').count(),
        'presupuestos_aprobados': presupuestos.filter(estado='aprobado').count(),
        'presupuestos_rechazados': presupuestos.filter(estado='rechazado').count(),
    }
    return render(request, 'cliente/cliente_presupuestos.html', context)


@login_required
@permission_required('seguridad.ver_clientes', raise_exception=True)
def cliente_ordenes(request, cliente_id):
    """Vista para mostrar las órdenes de trabajo de un cliente"""
    from orden_trabajo.models import OrdenTrabajo
    
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    
    # Obtener órdenes del cliente
    ordenes = OrdenTrabajo.objects.filter(cliente=cliente).order_by('-fecha_creacion')
    
    context = {
        'cliente': cliente,
        'ordenes': ordenes,
        'total_ordenes': ordenes.count(),
        'ordenes_pendientes': ordenes.filter(estado='pendiente').count(),
        'ordenes_proceso': ordenes.filter(estado__in=['en_proceso', 'espera_repuestos', 'pausado']).count(),
        'ordenes_completadas': ordenes.filter(estado='completado').count(),
        'ordenes_aprobadas': ordenes.filter(estado='aprobado').count(),
        'ordenes_facturadas': ordenes.filter(estado='facturado').count(),
    }
    return render(request, 'cliente/cliente_ordenes.html', context)


@login_required
@permission_required('seguridad.ver_clientes', raise_exception=True)
def cliente_facturas(request, cliente_id):
    """Vista para mostrar las facturas de un cliente"""
    from factura.models import Factura
    
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    
    # Obtener facturas del cliente
    facturas = Factura.objects.filter(cliente=cliente).order_by('-fecha', '-id')
    
    context = {
        'cliente': cliente,
        'facturas': facturas,
        'total_facturas': facturas.count(),
        'facturas_activas': facturas.filter(estado='ACTIVA').count(),
        'facturas_anuladas': facturas.filter(estado='ANULADA').count(),
        'facturas_entregadas': facturas.filter(entregada=True).count(),
    }
    return render(request, 'cliente/cliente_facturas.html', context)