from datetime import date
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import  models, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse
from cliente.models import Cliente
from vehiculo.models import Vehiculo
from servicio.models import Servicio
from .forms import PresupuestoForm, PresupuestoEditarForm, PresupuestoServicioForm, PresupuestoServicioFormSet
from .models import Presupuesto, PresupuestoServicio, BitacoraPresupuesto
from django.db.models import Q

# ============
# PRESUPUESTOS
# ============

@login_required
@permission_required('seguridad.agregar_presupuestos', raise_exception=True)
def presupuesto_crear(request):
    # OBTENER VEHÍCULO DE LA URL SI VIENE COMO PARÁMETRO
    vehiculo_id = request.GET.get('vehiculo')
    vehiculo_inicial = None
    cliente_inicial = None
    
    if vehiculo_id:
        try:
            vehiculo_inicial = Vehiculo.objects.get(pk=vehiculo_id)
            # Si el vehículo tiene propietario, usarlo como cliente inicial
            if vehiculo_inicial.propietario:
                cliente_inicial = vehiculo_inicial.propietario
            elif vehiculo_inicial.poseedor:
                cliente_inicial = vehiculo_inicial.poseedor
        except Vehiculo.DoesNotExist:
            messages.warning(request, "El vehículo especificado no existe")
    
    if request.method == "POST":
        form = PresupuestoForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear presupuesto sin servicios primero
                    presupuesto = form.save(commit=False)
                    
                    # ASIGNAR EL VEHÍCULO SI VIENE DE LA URL Y NO ESTÁ YA ASIGNADO
                    if vehiculo_inicial and not presupuesto.vehiculo:
                        presupuesto.vehiculo = vehiculo_inicial
                    
                    # ASIGNAR EL CLIENTE SI VIENE DEL VEHÍCULO Y NO ESTÁ YA ASIGNADO
                    if cliente_inicial and not presupuesto.cliente:
                        presupuesto.cliente = cliente_inicial
                    
                    # Establecer valores por defecto para evitar errores
                    presupuesto.subtotal_servicios = Decimal('0.00')
                    presupuesto.iva_monto = Decimal('0.00')
                    presupuesto.total = Decimal('0.00')
                    
                    # Guardar para obtener ID
                    presupuesto.save()
                    
                    # Procesar servicios
                    servicios_data = []
                    i = 0
                    while True:
                        servicio_key = f'servicios[{i}][servicio_id]'
                        cantidad_key = f'servicios[{i}][cantidad]'
                        
                        if servicio_key not in request.POST:
                            break
                            
                        servicio_id = request.POST.get(servicio_key)
                        cantidad = request.POST.get(cantidad_key)
                        
                        if servicio_id and cantidad:
                            servicios_data.append({
                                'servicio_id': servicio_id,
                                'cantidad': cantidad
                            })
                        i += 1
                    
                    # Crear servicios si hay datos
                    servicios_creados = 0
                    for servicio_info in servicios_data:
                        try:
                            servicio = Servicio.objects.get(id=servicio_info['servicio_id'])
                            PresupuestoServicio.objects.create(
                                presupuesto=presupuesto,
                                servicio=servicio,
                                cantidad=servicio_info['cantidad']
                            )
                            servicios_creados += 1
                        except Servicio.DoesNotExist:
                            continue
                    
                    # Solo actualizar totales si se crearon servicios
                    if servicios_creados > 0:
                        presupuesto.actualizar_totales()
                        presupuesto.save()

                    BitacoraPresupuesto.registrar(presupuesto, _("Creación de presupuesto"), "Presupuesto creado", request.user)
                    
                if servicios_creados == 1:
                    messages.success(request, f"Presupuesto #{presupuesto.id} creado con {servicios_creados} servicio")
                else:
                    messages.success(request, f"Presupuesto #{presupuesto.id} creado con {servicios_creados} servicios")
                    
                return redirect("presupuesto_lista") 

            except Exception as e:
                messages.error(request, f"Error al crear presupuesto: {str(e)}")
                print(f"Error detallado: {e}")
    else:
        # Pasar el vehículo y cliente inicial al formulario
        initial_data = {}
        if vehiculo_inicial:
            initial_data['vehiculo'] = vehiculo_inicial
        if cliente_inicial:
            initial_data['cliente'] = cliente_inicial
        
        form = PresupuestoForm(initial=initial_data)

    servicios_disponibles = Servicio.objects.filter(is_active=True)

    return render(request, "presupuesto/presupuesto_crear.html", {  
        "form": form,
        "servicios_disponibles": servicios_disponibles,
        "vehiculo_inicial": vehiculo_inicial,
        "cliente_inicial": cliente_inicial,
    })


@login_required
@permission_required('seguridad.ver_presupuestos', raise_exception=True)
def presupuesto_ver(request, presupuesto_id):
    presupuesto = get_object_or_404(Presupuesto, pk=presupuesto_id)
    servicios_presupuesto = presupuesto.presupuestoservicio_set.all().select_related('servicio').order_by('servicio__nombre')

    # Inicializar variables
    usuario_creacion = None
    usuario_actualizacion = None
    ultima_actualizacion = presupuesto.fecha_creacion
    
    # Obtener todas las entradas de bitácora ordenadas por fecha
    bitacoras = presupuesto.bitacora.all().order_by('fecha')
    
    if bitacoras.exists():
        # PRIMERA ENTRADA = CREACIÓN (siempre existe)
        primera_bitacora = bitacoras.first()
        usuario_creacion = primera_bitacora.usuario
        
        # SOLO si hay más de una entrada, hay actualización
        if bitacoras.count() > 1:
            # ÚLTIMA ENTRADA = ÚLTIMA ACTUALIZACIÓN (diferente de creación)
            ultima_bitacora = bitacoras.last()
            ultima_actualizacion = ultima_bitacora.fecha
            usuario_actualizacion = ultima_bitacora.usuario
        else:
            # Si solo hay una entrada, es la creación, no hay actualización
            usuario_actualizacion = None
            ultima_actualizacion = None

    if presupuesto.estado == 'pendiente' and date.today() >= presupuesto.fecha_vencimiento:
        presupuesto.estado = 'vencido'
        presupuesto.save(update_fields=['estado'])
        messages.info(request, "Este presupuesto ha sido marcado como VENCIDO automáticamente")

    if presupuesto.estado in ['aprobado', 'rechazado', 'vencido']:
        messages.info(request, f"El presupuesto con estado {presupuesto.get_estado_display().upper()} ya no puede ser modificado")

    if presupuesto.orden_trabajo_generada:
        messages.info(request, f"El presupuesto tiene una ORDEN DE TRABAJO asociada")

    if presupuesto.orden_trabajo_generada and not presupuesto.orden_trabajo:
        messages.error(request, "El presupuesto tiene OT generada, pero no se encontró la orden asociada")

    return render(request, "presupuesto/presupuesto_ver.html", {
        "presupuesto": presupuesto,
        "servicios_presupuesto": servicios_presupuesto,
        "usuario_creacion": usuario_creacion,
        "usuario_actualizacion": usuario_actualizacion,
        "ultima_actualizacion": ultima_actualizacion,
    })


@login_required
@permission_required('seguridad.editar_presupuestos', raise_exception=True)
def presupuesto_editar(request, presupuesto_id):
    try:
        presupuesto = get_object_or_404(Presupuesto, pk=presupuesto_id)
        puede_cambiar_estado = request.user.has_perm('seguridad.cambiar_estado_presupuestos')
        
        if request.method == "POST":
            form = PresupuestoEditarForm(request.POST, instance=presupuesto)
            formset = PresupuestoServicioFormSet(request.POST, instance=presupuesto)

            if form.is_valid():
                try:
                    with transaction.atomic():
                        presupuesto_actualizado = form.save(commit=False) 

                        # PROCESAR CAMBIO DE ESTADO
                        nuevo_estado = request.POST.get('estado')
                        if (puede_cambiar_estado and 
                            nuevo_estado in dict(Presupuesto.ESTADO_CHOICES)):
                            
                            if presupuesto.estado in ['rechazado', 'vencido']:
                                messages.error(request, f"No se puede cambiar el estado de un presupuesto {presupuesto.get_estado_display().upper()}")
                                return redirect("presupuesto_editar", presupuesto_id=presupuesto.id)
                            
                            if nuevo_estado == 'vencido':
                                messages.error(request, "El estado VENCIDO se asigna automáticamente")
                                return redirect("presupuesto_editar", presupuesto_id=presupuesto.id)
                            
                            if presupuesto.estado == 'aprobado' and nuevo_estado == 'pendiente':
                                messages.error(request, "No se puede volver a PENDIENTE desde APROBADO")
                                return redirect("presupuesto_editar", presupuesto_id=presupuesto.id)
                            
                            presupuesto_actualizado.estado = nuevo_estado
                        
                        # PROCESAR SERVICIOS ELIMINADOS PRIMERO
                        servicios_eliminados = request.POST.getlist('servicios_eliminados[]')
                        for servicio_presupuesto_id in servicios_eliminados:
                            try:
                                PresupuestoServicio.objects.get(
                                    id=servicio_presupuesto_id,
                                    presupuesto=presupuesto
                                ).delete()
                            except (PresupuestoServicio.DoesNotExist, ValueError):
                                pass
                        
                        # PROCESAR SERVICIOS EXISTENTES - ACTUALIZAR CANTIDADES
                        i = 0
                        while f'servicios_existentes[{i}][servicio_presupuesto_id]' in request.POST:
                            servicio_presupuesto_id = request.POST.get(f'servicios_existentes[{i}][servicio_presupuesto_id]')
                            nueva_cantidad = request.POST.get(f'servicios_existentes[{i}][cantidad]')
                            
                            if servicio_presupuesto_id and nueva_cantidad:
                                try:
                                    presupuesto_servicio = PresupuestoServicio.objects.get(
                                        id=servicio_presupuesto_id,
                                        presupuesto=presupuesto
                                    )
                                    cantidad_float = float(nueva_cantidad)
                                    
                                    if cantidad_float > 0:
                                        presupuesto_servicio.cantidad = cantidad_float
                                        presupuesto_servicio.save()
                                except (PresupuestoServicio.DoesNotExist, ValueError) as e:
                                    print(f"Error actualizando cantidad: {e}")
                            i += 1
                        
                        # PROCESAR NUEVOS SERVICIOS
                        i = 0
                        while f'servicios[{i}][servicio_id]' in request.POST:
                            servicio_id = request.POST.get(f'servicios[{i}][servicio_id]')
                            cantidad = request.POST.get(f'servicios[{i}][cantidad]')
                            
                            if servicio_id and cantidad:
                                try:
                                    servicio = Servicio.objects.get(id=servicio_id)
                                    if not PresupuestoServicio.objects.filter(
                                        presupuesto=presupuesto_actualizado,
                                        servicio=servicio
                                    ).exists():
                                        PresupuestoServicio.objects.create(
                                            presupuesto=presupuesto_actualizado,
                                            servicio=servicio,
                                            cantidad=cantidad
                                        )
                                except (Servicio.DoesNotExist, ValueError):
                                    pass
                            i += 1
                        
                        # GUARDAR Y ACTUALIZAR TOTALES
                        presupuesto_actualizado.save()
                        presupuesto_actualizado.actualizar_totales()
                        presupuesto_actualizado.save()
                        BitacoraPresupuesto.registrar(presupuesto_actualizado, _("Edición de presupuesto"), "Presupuesto actualizado", request.user)
                    
                    messages.success(request, f"Presupuesto #{presupuesto.id} actualizado")
                    return redirect("presupuesto_ver", presupuesto_id=presupuesto.id)
                    
                except Exception as e:
                    messages.error(request, f"Error al guardar: {str(e)}")
        else:

            form = PresupuestoEditarForm(instance=presupuesto)
            formset = PresupuestoServicioFormSet(instance=presupuesto)

        servicios_disponibles = Servicio.objects.filter(is_active=True)

        return render(request, "presupuesto/presupuesto_editar.html", {
            "form": form, 
            "formset": formset,
            "presupuesto": presupuesto, 
            "puede_cambiar_estado": puede_cambiar_estado,
            "servicios_disponibles": servicios_disponibles,
        })
        
    except Presupuesto.DoesNotExist:
        messages.error(request, "El presupuesto no existe.")
        return redirect("presupuesto_lista")
    except Exception as e:
        messages.error(request, f"Error al cargar el presupuesto: {str(e)}")
        return redirect("presupuesto_lista")


@login_required
@permission_required('seguridad.ver_presupuestos', raise_exception=True)
def presupuesto_lista(request):
    q = (request.GET.get("q") or "").strip() 
    estado = (request.GET.get("estado") or "").strip()
    cliente_id = (request.GET.get("cliente") or "").strip()
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    hoy = date.today()

    presupuestos_actualizados = Presupuesto.objects.filter(
        estado='pendiente',
        fecha_vencimiento__lt=hoy
    ).update(estado='vencido')
    
    if presupuestos_actualizados > 0:
        if presupuestos_actualizados == 1:
            messages.info(request, f"{presupuestos_actualizados} presupuesto marcado como VENCIDO automáticamente")
        else:
            messages.info(request, f"{presupuestos_actualizados} presupuestos marcados como VENCIDOS automáticamente")

    # Ahora obtener los datos para mostrar
    qs = Presupuesto.objects.all().select_related('cliente', 'vehiculo')

    # Filtros de búsqueda
    if q:
        qs = qs.filter(
            models.Q(id__icontains=q) |
            models.Q(cliente__nombre__icontains=q) |
            models.Q(vehiculo__nro_chapa__icontains=q) |
            models.Q(vehiculo__nro_chasis__icontains=q) |
            models.Q(vehiculo__marca__icontains=q) |
            models.Q(vehiculo__modelo__icontains=q) |
            models.Q(descripcion__icontains=q)
        )
    
    if estado:
        qs = qs.filter(estado=estado)
    
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    
    if fecha_desde:
        qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
    
    if fecha_hasta:
        qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

    # PAGINACIÓN
    paginator = Paginator(qs.order_by("-fecha_creacion"), 10)
    page = request.GET.get("page")
    presupuestos = paginator.get_page(page)

    # Parámetros para mantener en la paginación
    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    # Datos para filtros
    try:
        clientes = Cliente.objects.filter(estado='activo').order_by('nombre')
    except:
        clientes = Cliente.objects.all().order_by('nombre')
    
    estados = Presupuesto.ESTADO_CHOICES

    return render(request, "presupuesto/presupuesto_lista.html", {
        "presupuestos": presupuestos,
        "qs_no_page": qs_no_page,
        "clientes": clientes,
        "estados": estados,
    })


@login_required
@permission_required('seguridad.cambiar_estado_presupuestos', raise_exception=True)
def presupuesto_cambiar_estado(request, presupuesto_id):
    presupuesto = get_object_or_404(Presupuesto, pk=presupuesto_id)
    
    if request.method == "POST":
        nuevo_estado = request.POST.get('estado')
        origen = request.POST.get('origen', 'detalle')  # 'detalle' o 'lista'
        
        # VALIDAR TRANSICIONES DE ESTADO PERMITIDAS
        if nuevo_estado in dict(Presupuesto.ESTADO_CHOICES):
            
            # No permitir cambiar desde estados finales
            if presupuesto.estado in ['rechazado', 'vencido']:
                messages.error(request, f"No se puede cambiar el estado de un presupuesto {presupuesto.get_estado_display().upper()}")
                return redirect("presupuesto_ver", presupuesto_id=presupuesto.id)
            
            # No permitir cambiar a vencido manualmente
            if nuevo_estado == 'vencido':
                messages.error(request, "El estado VENCIDO se asigna automáticamente cuando caduca un presupuesto pendiente")
                return redirect("presupuesto_ver", presupuesto_id=presupuesto.id)
            
            # Validar transición desde aprobado
            if (presupuesto.estado == 'aprobado' and 
                nuevo_estado == 'pendiente'):
                messages.error(request, "No se puede volver a estado PENDIENTE una vez que el presupuesto ha sido APROBADO")
                return redirect("presupuesto_ver", presupuesto_id=presupuesto.id)
            
            # Validar que tenga servicios antes de aprobar
            if (nuevo_estado == 'aprobado' and 
                not presupuesto.tiene_servicios):
                messages.error(request, "No se puede aprobar un presupuesto sin servicios")
                if origen == 'lista':
                    return redirect("presupuesto_cambiar_estados")
                return redirect("presupuesto_ver", presupuesto_id=presupuesto.id)
            
            # Cambiar el estado
            estado_anterior = presupuesto.estado
            presupuesto.estado = nuevo_estado
            presupuesto.save(update_fields=["estado"])
            
            # Mensaje de éxito 
            estados_dict = dict(Presupuesto.ESTADO_CHOICES)
            mensaje = f"Presupuesto #{presupuesto.id} {presupuesto.get_estado_display().upper()}"
            messages.success(request, mensaje)
            
            # Redirigir según el origen
            if origen == 'lista':
                return redirect("presupuesto_cambiar_estados")
            else:
                return redirect("presupuesto_ver", presupuesto_id=presupuesto.id)
                
        else:
            messages.error(request, "Estado no válido.")
            if origen == 'lista':
                return redirect("presupuesto_cambiar_estados")
    
    # Redirigir según el origen por defecto
    if request.META.get('HTTP_REFERER', '').endswith('/cambiar-estados/'):
        return redirect("presupuesto_cambiar_estados")
    return redirect("presupuesto_ver", presupuesto_id=presupuesto.id)


@login_required
@permission_required('seguridad.cambiar_estado_presupuestos', raise_exception=True)
def presupuesto_cambiar_estados(request):
    """Vista específica para cambiar estados de presupuestos pendientes"""
    
    # Actualizar presupuestos vencidos automáticamente
    hoy = date.today()
    presupuestos_actualizados = Presupuesto.objects.filter(
        estado='pendiente',
        fecha_vencimiento__lt=hoy
    ).update(estado='vencido')
    
    if presupuestos_actualizados > 0:
        if presupuestos_actualizados == 1:
            messages.info(request, f"{presupuestos_actualizados} presupuesto marcado como VENCIDO automáticamente")
        else:
            messages.info(request, f"{presupuestos_actualizados} presupuestos marcados como VENCIDOS automáticamente")

    # Obtener solo presupuestos pendientes (no vencidos)
    qs = Presupuesto.objects.filter(estado='pendiente').select_related('cliente', 'vehiculo')
    
    # Filtros de búsqueda
    q = (request.GET.get("q") or "").strip()
    if q:
        # Si el query es numérico, buscar por ID exacto primero
        if q.isdigit():
            qs = qs.filter(
                Q(id=int(q)) |  # Búsqueda exacta por ID
                Q(cliente__nombre__icontains=q) |
                Q(vehiculo__nro_chapa__icontains=q) |
                Q(vehiculo__nro_chasis__icontains=q) |
                Q(vehiculo__marca__icontains=q) |
                Q(vehiculo__modelo__icontains=q)
            )
        else:
            # Si no es numérico, buscar solo en texto
            qs = qs.filter(
                Q(cliente__nombre__icontains=q) |
                Q(vehiculo__nro_chapa__icontains=q) |
                Q(vehiculo__nro_chasis__icontains=q) |
                Q(vehiculo__marca__icontains=q) |
                Q(vehiculo__modelo__icontains=q)
            )
    
    # PAGINACIÓN
    # Prioriza los que vencen pronto
    paginator = Paginator(qs.order_by("fecha_vencimiento", "-fecha_creacion"), 10)
    page = request.GET.get("page")
    presupuestos = paginator.get_page(page)

    # Parámetros para mantener en la paginación
    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    return render(request, "presupuesto/presupuesto_cambiar_estados.html", {
        "presupuestos": presupuestos,
        "qs_no_page": qs_no_page,
    })


# IMPRIMIR PRESUPUESTO
@login_required
@permission_required('seguridad.imprimir_presupuestos', raise_exception=True)
def presupuesto_imprimir(request, presupuesto_id):
    presupuesto = get_object_or_404(Presupuesto, pk=presupuesto_id)
    servicios_presupuesto = presupuesto.presupuestoservicio_set.all().select_related('servicio').order_by('servicio__nombre')
    
    return render(request, "presupuesto/presupuesto_imprimir.html", {
        "presupuesto": presupuesto,
        "servicios_presupuesto": servicios_presupuesto
    })


# GENERAR ORDEN DE TRABAJO (PRECARGAR DATOS)
@permission_required('presupuesto.gestionar_presupuestos', raise_exception=True)
def generar_orden_desde_presupuesto(request, presupuesto_id):
    """
    Vista para precargar datos en el formulario de orden de trabajo
    """
    presupuesto = get_object_or_404(Presupuesto, id=presupuesto_id)
    
    if presupuesto.estado != 'aprobado':
        messages.error(request, "Solo se pueden generar órdenes de trabajo desde presupuestos aprobados")
        return redirect('presupuesto_lista')
    
    # VERIFICAR SI YA EXISTE UNA OT
    if presupuesto.orden_trabajo_generada:
        messages.error(request, "Ya se generó una orden de trabajo desde este presupuesto. Solo se permite una OT por presupuesto")
        return redirect('presupuesto_lista')
    

    response = redirect('orden_trabajo_crear')
    response['Location'] += f'?presupuesto_id={presupuesto_id}'
    return response
    
    
# Vista auxiliar para obtener vehículos
@login_required
def obtener_vehiculos_cliente(request, cliente_id):
    """Vista para obtener todos los vehículos (ya no filtramos por cliente)"""
    try:
        vehiculos = Vehiculo.objects.filter(estado='activo').values('id', 'nro_chapa', 'nro_chasis', 'marca', 'modelo').order_by('marca', 'modelo')
    except:
        vehiculos = Vehiculo.objects.all().values('id', 'nro_chapa', 'marca', 'modelo').order_by('marca', 'modelo')
    return JsonResponse(list(vehiculos), safe=False)


# BÚSQUEDAS
@login_required
def buscar_clientes_autocomplete(request):
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
def buscar_vehiculos_autocomplete(request):
    """Vista para autocompletar vehículos - CON MANEJO COMPLETO DE ERRORES"""
    query = request.GET.get('q', '').strip()
    
    try:
        
        # Obtener todos los vehículos
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
        
        # Formatear respuesta
        vehiculos_data = []
        for vehiculo in vehiculos:
            vehiculos_data.append({
                'id': vehiculo.pk,
                'text': f"{vehiculo.marca} {vehiculo.modelo} - {vehiculo.nro_chapa} - {vehiculo.nro_chasis}",
                'chapa': vehiculo.nro_chapa or 'Sin chapa',
                'chasis': vehiculo.nro_chasis or 'Sin chasis',
                'marca': vehiculo.marca or 'Sin marca',
                'modelo': vehiculo.modelo or 'Sin modelo',
            })
        
        return JsonResponse(vehiculos_data, safe=False)
        
    except ImportError:
        return JsonResponse([{'id': '', 'text': 'Error: Modelo no disponible'}], safe=False)
        
    except Exception as e:
        return JsonResponse([], safe=False)

