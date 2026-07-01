from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db import models  
from .services import ComisionService, TiempoRealService
from .models import RegistroTiempoReal, RevisionServicio
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from cliente.models import Cliente
from orden_trabajo.services import ControlCargaService
from servicio.models import Servicio
from presupuesto.models import Presupuesto
from seguridad.models import ConfiguracionSistema
from vehiculo.models import Vehiculo
from empleado.models import Empleado
from orden_trabajo.services import ControlCargaService
from .forms import (
    TRANSICIONES_PERMITIDAS,
    OrdenTrabajoForm,
    OrdenTrabajoEditarForm,
    OrdenServicioFormSet,
    AsignacionOrdenForm,
)
from .models import (
    OrdenTrabajo,
    OrdenServicio,
    AsignacionOrden,
    BitacoraOrden,
    ESTADOS_ORDEN
)


# ==================
# ORDENES DE TRABAJO
# ==================

@login_required
@permission_required('seguridad.agregar_ordenes_trabajo', raise_exception=True)
def orden_trabajo_crear(request):
    # VARIABLES PARA PRECARGAR DESDE PRESUPUESTO
    presupuesto_origen = None
    servicios_iniciales = []
    
    # PRECARGAR DATOS SI VIENE DESDE PRESUPUESTO (SOLO EN GET)
    if request.method == "GET" and 'presupuesto_id' in request.GET:
        presupuesto_id = request.GET.get('presupuesto_id')
        try:
            presupuesto_origen = Presupuesto.objects.get(id=presupuesto_id, estado='aprobado')
            
            # Crear formulario con datos precargados 
            form = OrdenTrabajoForm(initial={
                'cliente': presupuesto_origen.cliente,
                'vehiculo': presupuesto_origen.vehiculo,
                'descripcion': presupuesto_origen.descripcion
            })
            
            # Preparar servicios iniciales desde el presupuesto 
            for ps in presupuesto_origen.presupuestoservicio_set.select_related('servicio').all():
                servicio_data = {
                    'servicio': ps.servicio,
                    'cantidad': ps.cantidad,
                    'nombre': ps.servicio.nombre,
                    'tiempo_min_estimado': ps.servicio.tiempo_min_estimado or 0,
                    'categoria': ps.servicio.categoria or 'Sin categoría'
                }
                servicios_iniciales.append(servicio_data)
            
            messages.info(request, f"Orden precargada desde PRESUPUESTO #{presupuesto_origen.id}")
            
        except Presupuesto.DoesNotExist:
            messages.error(request, "Presupuesto no encontrado o no está aprobado")
            form = OrdenTrabajoForm()
        except Exception as e:
            messages.error(request, f"Error al cargar presupuesto: {str(e)}")
            form = OrdenTrabajoForm()
    else:
        form = OrdenTrabajoForm()

    # PROCESAR FORMULARIO POST
    if request.method == "POST":
        form = OrdenTrabajoForm(request.POST) 
        
        # Validaciones previas
        servicios_count = 0
        empleados_count = 0
        
        i = 0
        while f'servicios[{i}][servicio_id]' in request.POST:
            servicio_id = request.POST.get(f'servicios[{i}][servicio_id]')
            if servicio_id and servicio_id.strip():
                servicios_count += 1
                
                j = 0
                while f'servicios[{i}][empleados][{j}][empleado_id]' in request.POST:
                    empleado_id = request.POST.get(f'servicios[{i}][empleados][{j}][empleado_id]')
                    if empleado_id and empleado_id.strip() and empleado_id.isdigit(): 
                        empleados_count += 1
                    j += 1
            i += 1
        
        if servicios_count == 0:
            messages.error(request, "Debe agregar al menos un servicio")
        elif empleados_count == 0:
            messages.error(request, "Debe asignar al menos un empleado a los servicios")
        elif form.is_valid():
            try:
                with transaction.atomic():
                    ot = form.save(commit=False)
                    ot.subtotal_servicios = Decimal('0.00')
                    ot.total = Decimal('0.00')
                    
                    # CAPTURAR PRESUPUESTO_ID
                    presupuesto_id_post = request.POST.get('presupuesto_id')
                    
                    # Si venía de presupuesto, guardar la referencia
                    if presupuesto_id_post and presupuesto_id_post.isdigit():
                        try:
                            presupuesto_origen_post = Presupuesto.objects.get(id=int(presupuesto_id_post))
                            ot.presupuesto_origen = presupuesto_origen_post

                            ot.iva_porcentaje = presupuesto_origen_post.iva_porcentaje
                            ot.descuento = presupuesto_origen_post.descuento

                        except (Presupuesto.DoesNotExist, ValueError):

                            ot.descuento = Decimal('0.00')
                            ot.iva_porcentaje = 10
                    else: 
                        ot.descuento = Decimal('0.00')
                        ot.iva_porcentaje = 10
                    
                    ot.save()

                    # Procesar servicios
                    i = 0
                    servicios_creados = 0
                    empleados_asignaciones_totales = 0
                    
                    while f'servicios[{i}][servicio_id]' in request.POST:
                        servicio_id = request.POST.get(f'servicios[{i}][servicio_id]')
                        cantidad = request.POST.get(f'servicios[{i}][cantidad]')
                        
                        if servicio_id and servicio_id.strip() and cantidad and cantidad.strip():
                            try:
                                servicio_id_int = int(servicio_id)
                                cantidad_decimal = Decimal(cantidad)
                                
                                srv = Servicio.objects.get(id=servicio_id_int)
                                nuevo_servicio = OrdenServicio.objects.create(
                                    orden=ot,
                                    servicio=srv,
                                    cantidad=cantidad_decimal,
                                    precio_unitario=srv.precio_base or Decimal('0.00'),
                                )
                                servicios_creados += 1
                                
                                # Procesar empleados
                                j = 0
                                empleados_asignados_servicio = 0
                                while f'servicios[{i}][empleados][{j}][empleado_id]' in request.POST:
                                    empleado_id = request.POST.get(f'servicios[{i}][empleados][{j}][empleado_id]')
                                    
                                    if empleado_id and empleado_id.strip() and empleado_id.isdigit():
                                        try:
                                            empleado_id_int = int(empleado_id)
                                            empleado = Empleado.objects.get(id_empleado=empleado_id_int)
                                            AsignacionOrden.objects.create(
                                                orden=ot,
                                                empleado=empleado,
                                                servicio=nuevo_servicio,
                                                estado='asignado'
                                            )
                                            empleados_asignados_servicio += 1
                                            empleados_asignaciones_totales += 1
                                        except (Empleado.DoesNotExist, ValueError):
                                            pass
                                    j += 1
                                
                                if empleados_asignados_servicio == 0:
                                    messages.error(request, f"El servicio '{srv.nombre}' no tiene empleados asignados")
                                    
                            except (Servicio.DoesNotExist, ValueError, InvalidOperation) as e:
                                messages.error(request, f"Error con el servicio ID {servicio_id}: {str(e)}")
                        i += 1

                    ot.actualizar_totales(save=True)
                    BitacoraOrden.registrar(ot, _("Creación de orden de trabajo"), "Orden creada", request.user)

                    # ACTUALIZAR EL PRESUPUESTO
                    if presupuesto_id_post and presupuesto_id_post.isdigit():
                        try:
                            presupuesto = Presupuesto.objects.get(id=int(presupuesto_id_post))
                            presupuesto.orden_trabajo_generada = True
                            presupuesto.orden_trabajo = ot  
                            presupuesto.save(update_fields=['orden_trabajo_generada', 'orden_trabajo'])
                            
                            # messages.info(request, f"Presupuesto #{presupuesto.id} vinculado a OT #{ot.id}")
                            
                        except Presupuesto.DoesNotExist:
                            pass

                messages.success(request, f"Orden #{ot.id} creada con {servicios_creados} servicio(s) y {empleados_asignaciones_totales} asignación(es)")
                # MOSTRAR INFO SI VIENE DE PRESUPUESTO
                if presupuesto_id_post and presupuesto_id_post.isdigit():
                    mensaje_info = f"IVA {ot.iva_porcentaje}%"
                    if ot.descuento > Decimal('0.00'):
                        mensaje_info += f" y descuento de Gs. {ot.descuento:,.0f}"
                    messages.info(request, f"Desde su presupuesto: {mensaje_info}")
                return redirect("orden_trabajo_ver", orden_id=ot.id)

            except Exception as e:
                messages.error(request, f"Error al crear orden: {str(e)}")

    # PREPARAR DATOS PARA EL TEMPLATE
    servicios_disponibles = Servicio.objects.filter(is_active=True)
    empleados_disponibles = Empleado.objects.filter(estado=True).order_by('nombre')

    # Pasar información del IVA del presupuesto si existe
    iva_presupuesto = None
    if presupuesto_origen:
        iva_presupuesto = presupuesto_origen.iva_porcentaje

    return render(request, "orden_trabajo/orden_trabajo_crear.html", {
        "form": form,
        "servicios_disponibles": servicios_disponibles,
        "empleados_disponibles": empleados_disponibles,
        "presupuesto_origen": presupuesto_origen,
        "servicios_iniciales": servicios_iniciales,
        "iva_presupuesto": iva_presupuesto,
    })


@login_required
@permission_required('seguridad.ver_ordenes_trabajo', raise_exception=True)
def orden_trabajo_ver(request, orden_id):
    ot = get_object_or_404(OrdenTrabajo.objects.select_related("cliente", "vehiculo"), pk=orden_id)
    servicios = ot.ordenservicio_set.select_related('servicio').order_by('servicio__nombre')

    # Inicializar variables
    usuario_creacion = None
    usuario_actualizacion = None
    ultima_actualizacion = ot.fecha_creacion
    
    # Obtener todas las entradas de bitácora ordenadas por fecha
    bitacoras = ot.bitacora.all().order_by('fecha')
    
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
    
    # Si no hay bitácora pero la orden fue editada, usar fecha_creacion
    # (para ordenes nuevas que nunca fueron editadas)

    if ot.estado in ['completado', 'cancelado', 'facturado', 'aprobado', 'en_revision']:
        messages.info(request, f"La orden con estado {ot.get_estado_display().upper()} ya no puede ser modificada")

    # Obtener asignaciones con conteo de servicios por empleado 
    asignaciones_con_contador = []
    for asignacion in ot.asignaciones.select_related('empleado', 'servicio').order_by('-fecha_asignacion'):
        # Contar cuántos servicios tiene asignado este empleado en esta orden
        servicios_count = AsignacionOrden.objects.filter(
            orden=ot,
            empleado=asignacion.empleado
        ).count()
        
        asignaciones_con_contador.append({
            'asignacion': asignacion,
            'servicios_count': servicios_count
        })

    form_asignacion = None
    if request.user.has_perm('seguridad.editar_ordenes') and ot.es_editable:
        form_asignacion = AsignacionOrdenForm(orden=ot)  

    return render(request, "orden_trabajo/orden_trabajo_ver.html", {
        "orden": ot,
        "servicios": servicios,
        "asignaciones_con_contador": asignaciones_con_contador, 
        "form_asignacion": form_asignacion,
        "usuario_creacion": usuario_creacion,
        "usuario_actualizacion": usuario_actualizacion,
        "ultima_actualizacion": ultima_actualizacion,
    })


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def orden_trabajo_editar(request, orden_id):
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    puede_cambiar_estado = request.user.has_perm('seguridad.cambiar_estado_ordenes')

    # ============================================
    # VALIDACIÓN PARA ÓRDENES RECHAZADAS
    # ============================================
    es_orden_rechazada = (ot.estado == 'rechazado')
    servicios_rechazados_ids = []
    servicios_bloqueados = []
    mensaje_bloqueo = ""
    
    if es_orden_rechazada:
        # Obtener IDs de servicios rechazados (los que pueden modificarse)
        servicios_rechazados_ids = list(ot.servicios_rechazados)
        
        # Obtener servicios que NO pueden modificarse (aprobados)
        servicios_bloqueados = ot.ordenservicio_set.exclude(id__in=servicios_rechazados_ids)
        
        mensaje_bloqueo = "Esta orden fue RECHAZADA en revisión. SOLO puede modificar los servicios RECHAZADOS. Los servicios aprobados están BLOQUEADOS."

    # ============================================
    # OBTENER SERVICIOS CON SUS ASIGNACIONES ESPECÍFICAS
    # ============================================
    servicios_con_empleados = []
    for servicio_orden in ot.ordenservicio_set.select_related('servicio').all():
        # Verificar si este servicio puede modificarse (si es rechazado o no)
        puede_modificarse = True
        if es_orden_rechazada:
            puede_modificarse = servicio_orden.id in servicios_rechazados_ids
        
        empleados_asignados = Empleado.objects.filter(
            asignaciones__servicio=servicio_orden
        ).distinct()
        
        servicios_con_empleados.append({
            'servicio_orden': servicio_orden,
            'empleados': empleados_asignados,
            'puede_modificarse': puede_modificarse,  
            'esta_aprobado': servicio_orden.id not in servicios_rechazados_ids if es_orden_rechazada else None
        })

    # ============================================
    # PROCESAMIENTO POST
    # ============================================
    if request.method == "POST":
        form = OrdenTrabajoEditarForm(request.POST, instance=ot)
        
        # INICIALIZAR VARIABLES PARA VALIDACIÓN
        servicios_count = 0
        empleados_count = 0
        servicios_sin_empleados = []
        
        # ============================================
        # VALIDACIÓN PARA ÓRDENES RECHAZADAS
        # ============================================
        if es_orden_rechazada:
            # Verificar que NO se esté intentando modificar servicios aprobados
            # Obtener IDs de servicios que se intentan eliminar
            servicios_eliminados_raw = request.POST.getlist('servicios_eliminados[]')
            servicios_eliminados = [sid for sid in servicios_eliminados_raw if sid and sid.strip() and sid.isdigit()]
            servicios_eliminados_ids = [int(sid) for sid in servicios_eliminados]
            
            # Verificar que ningún servicio aprobado esté en la lista de eliminados
            servicios_aprobados_eliminados = set(servicios_eliminados_ids) - set(servicios_rechazados_ids)
            if servicios_aprobados_eliminados:
                servicios_nombres = OrdenServicio.objects.filter(id__in=servicios_aprobados_eliminados).values_list('servicio__nombre', flat=True)
                messages.error(request, f"No puede eliminar servicios APROBADOS. {', '.join(servicios_nombres)}")
                return redirect("orden_trabajo_editar", orden_id=ot.id)
            
            # Verificar modificaciones en cantidades de servicios existentes
            for servicio in ot.ordenservicio_set.all():
                if servicio.id not in servicios_rechazados_ids:
                    # Es un servicio aprobado - verificar que no se modifique su cantidad
                    field_name = f'servicios_existentes[{servicio.id}][cantidad]'
                    if field_name in request.POST:
                        nueva_cantidad = request.POST.get(field_name)
                        if nueva_cantidad and nueva_cantidad.strip():
                            try:
                                nueva_cantidad_decimal = Decimal(nueva_cantidad.strip().replace(',', '.'))
                                if nueva_cantidad_decimal != servicio.cantidad:
                                    messages.error(request, f"No puede modificar la cantidad del servicio APROBADO '{servicio.servicio.nombre}'")
                                    return redirect("orden_trabajo_editar", orden_id=ot.id)
                            except:
                                pass
        
        # Filtrar servicios_eliminados (considerando solo los permitidos)
        servicios_eliminados_raw = request.POST.getlist('servicios_eliminados[]')
        servicios_eliminados = [sid for sid in servicios_eliminados_raw if sid and sid.strip() and sid.isdigit()]
        
        # Si es orden rechazada, solo permitir eliminar servicios rechazados
        if es_orden_rechazada:
            servicios_eliminados = [sid for sid in servicios_eliminados if int(sid) in servicios_rechazados_ids]
        
        servicios_eliminados_ids = [int(sid) for sid in servicios_eliminados]
        
        # Contar servicios existentes que no se eliminarán
        servicios_existentes_count = ot.ordenservicio_set.exclude(id__in=servicios_eliminados_ids).count()
        servicios_count += servicios_existentes_count
        
        # Contar servicios nuevos
        i = 0
        servicios_nuevos_list = []
        while f'servicios_nuevos[{i}][servicio_id]' in request.POST:
            servicio_id = request.POST.get(f'servicios_nuevos[{i}][servicio_id]')
            if servicio_id and servicio_id.strip():
                servicios_count += 1
                servicios_nuevos_list.append(i)
                
                j = 0
                empleados_servicio_count = 0
                while f'servicios_nuevos[{i}][empleados][{j}][empleado_id]' in request.POST:
                    empleado_id = request.POST.get(f'servicios_nuevos[{i}][empleados][{j}][empleado_id]')
                    if empleado_id and empleado_id.strip() and empleado_id.isdigit():
                        empleados_servicio_count += 1
                        empleados_count += 1
                    j += 1
                
                if empleados_servicio_count == 0:
                    servicio_nombre = "Servicio nuevo"
                    try:
                        servicio_obj = Servicio.objects.get(id=servicio_id)
                        servicio_nombre = servicio_obj.nombre
                    except Servicio.DoesNotExist:
                        pass
                    servicios_sin_empleados.append(servicio_nombre)
            i += 1
        
        # Contar empleados de servicios existentes (solo servicios no eliminados)
        for servicio in ot.ordenservicio_set.exclude(id__in=servicios_eliminados_ids):
            # Contar empleados que no se eliminaron
            empleados_eliminados_raw = request.POST.getlist(f'servicios_existentes[{servicio.id}][empleados_eliminados][]')
            empleados_eliminados = [int(eid) for eid in empleados_eliminados_raw if eid and eid.strip() and eid.isdigit()]
            
            # Contar empleados nuevos que se agregaron
            empleados_nuevos_count = 0
            j = 0
            while True:
                field_name = f'servicios_existentes[{servicio.id}][empleados_nuevos][{j}][empleado_id]'
                if field_name not in request.POST:
                    break
                empleado_id = request.POST.get(field_name)
                if empleado_id and empleado_id.strip() and empleado_id.isdigit():
                    empleados_nuevos_count += 1
                j += 1
            
            # Empleados totales para este servicio
            empleados_originales = servicio.asignacionorden_set.count()
            empleados_finales = (empleados_originales - len(empleados_eliminados)) + empleados_nuevos_count
            
            # Validar que cada servicio tenga al menos un empleado
            if empleados_finales <= 0:
                servicios_sin_empleados.append(servicio.servicio.nombre)
            
            empleados_count += max(0, empleados_finales)

        # Validaciones generales
        errores_validacion = []
        
        if servicios_count == 0:
            errores_validacion.append("Debe haber al menos un servicio en la orden")
        
        if empleados_count == 0:
            errores_validacion.append("Debe asignar al menos un empleado a los servicios")
        
        if servicios_sin_empleados:
            errores_validacion.append(f"Los siguientes servicios no tienen empleados asignados: {', '.join(servicios_sin_empleados)}")
        
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    errores_validacion.append(f"Error en {field}: {error}")
        
        if errores_validacion:
            for error in errores_validacion:
                messages.error(request, error)
        else:
            try:
                with transaction.atomic():
                    ot_actualizada = form.save(commit=False)
                    
                    # Cambio de estado (con nuevas validaciones)
                    if puede_cambiar_estado:
                        nuevo_estado = request.POST.get('estado')
                        if nuevo_estado:
                            # Estados que no permiten cambio
                            estados_finales = ['completado', 'cancelado', 'rechazado', 'aprobado', 'facturado', 'en_revision']
                            if ot.estado in estados_finales:
                                messages.error(request, f"No se puede cambiar el estado de una orden en estado {ot.get_estado_display()}")
                                return redirect("orden_trabajo_editar", orden_id=ot.id)
                            
                            # Si es orden rechazada y se intenta cambiar a en_proceso
                            if ot.estado == 'rechazado' and nuevo_estado == 'en_proceso':
                                # Esto se maneja con el botón específico, no desde aquí
                                messages.info(request, "Para reanudar una orden rechazada, use el botón 'Reanudar Orden'")
                                return redirect("orden_trabajo_editar", orden_id=ot.id)
                            
                            ot_actualizada.estado = nuevo_estado
                    
                    # Guardar primero los cambios en la orden
                    ot_actualizada.save()

                    # ============================================
                    # 1. Procesar servicios eliminados
                    # ============================================
                    if servicios_eliminados_ids:
                        AsignacionOrden.objects.filter(servicio_id__in=servicios_eliminados_ids).delete()
                        OrdenServicio.objects.filter(id__in=servicios_eliminados_ids, orden=ot).delete()
                    
                    # ============================================
                    # 2. Procesar servicios existentes (actualizar cantidades)
                    # ============================================
                    for servicio in ot.ordenservicio_set.exclude(id__in=servicios_eliminados_ids):
                        # Verificar si este servicio puede modificarse (solo si es rechazado)
                        if es_orden_rechazada and servicio.id not in servicios_rechazados_ids:
                            # Servicio aprobado - saltar procesamiento
                            continue
                        
                        # OBTENER LA NUEVA CANTIDAD
                        nueva_cantidad = None
                        field_name = f'servicios_existentes[{servicio.id}][cantidad]'
                        if field_name in request.POST:
                            nueva_cantidad = request.POST.get(field_name)
                        elif f'cantidad_{servicio.id}' in request.POST:
                            nueva_cantidad = request.POST.get(f'cantidad_{servicio.id}')
                        else:
                            for key in request.POST.keys():
                                if str(servicio.id) in key and 'cantidad' in key:
                                    nueva_cantidad = request.POST.get(key)
                                    break
                        
                        if nueva_cantidad and nueva_cantidad.strip():
                            try:
                                cantidad_limpia = nueva_cantidad.strip()
                                if ',' in cantidad_limpia:
                                    cantidad_limpia = cantidad_limpia.replace(',', '.')
                                
                                servicio.cantidad = Decimal(cantidad_limpia)
                                servicio.save(update_fields=['cantidad'])
                                
                                # Marcar que fue modificado después del rechazo
                                if es_orden_rechazada:
                                    servicio.modificado_despues_rechazo = True
                                    servicio.save(update_fields=['modificado_despues_rechazo'])
                                
                            except (InvalidOperation, ValueError, TypeError) as e:
                                messages.warning(request, f"Error en cantidad del servicio {servicio.servicio.nombre}: {e}")
                        
                        # Procesar empleados eliminados
                        empleados_eliminados_raw = request.POST.getlist(f'servicios_existentes[{servicio.id}][empleados_eliminados][]')
                        empleados_eliminados = [int(eid) for eid in empleados_eliminados_raw if eid and eid.strip() and eid.isdigit()]
                        
                        if empleados_eliminados:
                            AsignacionOrden.objects.filter(
                                servicio=servicio,
                                empleado_id__in=empleados_eliminados
                            ).delete()
                        
                        # Procesar empleados nuevos
                        empleados_nuevos = []
                        j = 0
                        while True:
                            empleado_id = request.POST.get(f'servicios_existentes[{servicio.id}][empleados_nuevos][{j}][empleado_id]')
                            if not empleado_id:
                                break
                            if empleado_id and empleado_id.strip() and empleado_id.isdigit():
                                empleados_nuevos.append(int(empleado_id))
                            j += 1

                        for empleado_id in empleados_nuevos:
                            try:
                                empleado = Empleado.objects.get(pk=empleado_id)
                                if not AsignacionOrden.objects.filter(
                                    servicio=servicio,
                                    empleado=empleado
                                ).exists():
                                    AsignacionOrden.objects.create(
                                        orden=ot_actualizada,
                                        empleado=empleado,
                                        servicio=servicio,
                                        estado='asignado'
                                    )
                            except (Empleado.DoesNotExist, ValueError) as e:
                                messages.warning(request, f"Empleado ID {empleado_id} no encontrado: {str(e)}")
                                continue
                    
                    # ============================================
                    # 3. Procesar servicios NUEVOS
                    # ============================================
                    i = 0
                    while f'servicios_nuevos[{i}][servicio_id]' in request.POST:
                        servicio_id = request.POST.get(f'servicios_nuevos[{i}][servicio_id]')
                        cantidad = request.POST.get(f'servicios_nuevos[{i}][cantidad]')
                        
                        if servicio_id and servicio_id.strip() and cantidad and cantidad.strip():
                            try:
                                servicio_id_int = int(servicio_id)
                                cantidad_decimal = Decimal(cantidad)
                                
                                srv = Servicio.objects.get(id=servicio_id_int)
                                nuevo_servicio = OrdenServicio.objects.create(
                                    orden=ot_actualizada,
                                    servicio=srv,
                                    cantidad=cantidad_decimal,
                                    precio_unitario=srv.precio_base or Decimal('0.00'),
                                )
                                
                                # Marcar como modificado si es orden rechazada
                                if es_orden_rechazada:
                                    nuevo_servicio.modificado_despues_rechazo = True
                                    nuevo_servicio.save(update_fields=['modificado_despues_rechazo'])
                                
                                # Procesar empleados para este servicio nuevo
                                j = 0
                                empleados_asignados = 0
                                while f'servicios_nuevos[{i}][empleados][{j}][empleado_id]' in request.POST:
                                    empleado_id = request.POST.get(f'servicios_nuevos[{i}][empleados][{j}][empleado_id]')
                                    
                                    if empleado_id and empleado_id.strip() and empleado_id.isdigit():
                                        try:
                                            empleado_id_int = int(empleado_id)
                                            empleado = Empleado.objects.get(pk=empleado_id_int)
                                            AsignacionOrden.objects.create(
                                                orden=ot_actualizada,
                                                empleado=empleado,
                                                servicio=nuevo_servicio,
                                                estado='asignado'
                                            )
                                            empleados_asignados += 1
                                        except (Empleado.DoesNotExist, ValueError) as e:
                                            messages.warning(request, f"Empleado ID {empleado_id} no encontrado: {str(e)}")
                                    j += 1
                                
                                if empleados_asignados == 0:
                                    messages.warning(request, f"El servicio nuevo '{srv.nombre}' no tiene empleados asignados válidos")
                                    
                            except (Servicio.DoesNotExist, ValueError, InvalidOperation) as e:
                                messages.error(request, f"Error con el servicio nuevo ID {servicio_id}: {str(e)}")
                        i += 1

                    # Actualizar totales de la orden
                    ot_actualizada.actualizar_totales(save=True)
                    
                    # Registrar en bitácora
                    BitacoraOrden.registrar(ot_actualizada, _("Edición de orden"), "Orden actualizada", request.user)

                    messages.success(request, f"Orden #{ot.id} actualizada")
                    return redirect("orden_trabajo_ver", orden_id=ot.id)

            except (DjangoValidationError, ValidationError) as e:
                messages.error(request, f"Validación: {e}")
            except Exception as e:
                messages.error(request, f"Error al guardar: {str(e)}")
                import traceback
                traceback.print_exc()
    
    else:  # GET request
        form = OrdenTrabajoEditarForm(instance=ot)

    servicios_disponibles = Servicio.objects.filter(is_active=True)
    empleados_disponibles = Empleado.objects.filter(estado=True).order_by('nombre')
    
    return render(request, "orden_trabajo/orden_trabajo_editar.html", {
        "form": form,
        "orden": ot,
        "servicios_con_empleados": servicios_con_empleados,
        "puede_cambiar_estado": puede_cambiar_estado,
        "servicios_disponibles": servicios_disponibles,
        "empleados_disponibles": empleados_disponibles,
        # Variables adicionales para el template
        "es_orden_rechazada": es_orden_rechazada,
        "servicios_rechazados_ids": servicios_rechazados_ids,
        "servicios_bloqueados": servicios_bloqueados,
        "mensaje_bloqueo": mensaje_bloqueo,
    })


@login_required
@permission_required('seguridad.ver_ordenes_trabajo', raise_exception=True)
def orden_trabajo_lista(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    cliente_id = (request.GET.get("cliente") or "").strip()
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    qs = OrdenTrabajo.objects.all().select_related('cliente', 'vehiculo')

    if q:
        qs = qs.filter(
            Q(id__icontains=q) |
            Q(cliente__nombre__icontains=q) |
            Q(vehiculo__nro_chapa__icontains=q) |
            Q(vehiculo__nro_chasis__icontains=q) |
            Q(vehiculo__marca__icontains=q) |
            Q(vehiculo__modelo__icontains=q) |
            Q(descripcion__icontains=q)
        )
    if estado:
        qs = qs.filter(estado=estado)
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if fecha_desde:
        qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

    paginator = Paginator(qs.order_by("-fecha_creacion"), 10)
    page = request.GET.get("page")
    ordenes = paginator.get_page(page)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    try:
        clientes = Cliente.objects.filter(estado='activo').order_by('nombre')
    except Exception:
        clientes = Cliente.objects.all().order_by('nombre')

    estados = OrdenTrabajo._meta.get_field('estado').choices

    return render(request, "orden_trabajo/orden_trabajo_lista.html", {
        "ordenes": ordenes,
        "qs_no_page": qs_no_page,
        "clientes": clientes,
        "estados": estados,
    })


@login_required
@permission_required('seguridad.cambiar_estado_ordenes_trabajo', raise_exception=True)
def orden_trabajo_cambiar_estado(request, orden_id):
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)

    if request.method == "POST":
        nuevo_estado = request.POST.get('estado')
        origen = request.POST.get('origen', 'detalle')

        if nuevo_estado in dict(OrdenTrabajo._meta.get_field('estado').choices):
            if ot.estado in ['facturado', 'cancelado']:
                messages.error(request, f"No se puede cambiar el estado de una orden {ot.get_estado_display().upper()}")
                if origen == 'lista':
                    return redirect("orden_trabajo_cambiar_estados")
                return redirect("orden_trabajo_ver", orden_id=ot.id)

            if nuevo_estado not in TRANSICIONES_PERMITIDAS.get(ot.estado, []):
                estados_permitidos = [ot._get_estado_display(e) for e in TRANSICIONES_PERMITIDAS[ot.estado]]
                messages.error(
                    request, 
                    f"No se puede cambiar de '{ot.get_estado_display()}' a '{ot._get_estado_display(nuevo_estado)}'. "
                    f"Transiciones permitidas: {', '.join(estados_permitidos)}"
                )
                if origen == 'lista':
                    return redirect("orden_trabajo_cambiar_estados")
                return redirect("orden_trabajo_ver", orden_id=ot.id)

            estado_anterior = ot.estado

                    
            # VALIDACIÓN ESPECIAL PARA COMPLETADO
            if nuevo_estado == 'completado':
                try:
                    servicios = ot.ordenservicio_set.all()
                    
                    if not servicios.exists():
                        if origen == 'lista':
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return JsonResponse({
                                    'success': False,
                                    'error': 'validacion',
                                    'servicios_pendientes': [],
                                    'mensaje': 'La orden no tiene servicios asignados'
                                })
                            messages.error(request, "La orden no tiene servicios asignados")
                            return redirect("orden_trabajo_cambiar_estados")
                        return redirect("orden_trabajo_ver", orden_id=ot.id)
                    
                    # Verificar cada servicio
                    servicios_no_finalizados = []
                    
                    for servicio_orden in servicios:
                        # Si el servicio ya está marcado como finalizado por empleado, está OK
                        if servicio_orden.empleado_finalizado:
                            continue
                        
                        # Verificar si tiene registros de tiempo finalizados
                        # Buscar si hay algún registro finalizado para este servicio
                        tiene_registro_finalizado = RegistroTiempoReal.objects.filter(
                            servicio_orden=servicio_orden,
                            estado='finalizado'
                        ).exists()
                        
                        if tiene_registro_finalizado:
                            # El servicio tiene registros finalizados pero no está marcado
                            # Lo marcamos automáticamente
                            servicio_orden.empleado_finalizado = True
                            servicio_orden.fecha_finalizacion_empleado = timezone.now()
                            servicio_orden.save(update_fields=['empleado_finalizado', 'fecha_finalizacion_empleado'])
                            continue
                        
                        # Verificar si tiene empleados activos
                        asignaciones_activas = AsignacionOrden.objects.filter(
                            servicio=servicio_orden,
                            estado__in=['asignado', 'en_ejecucion']
                        ).exists()
                        
                        if not asignaciones_activas:
                            # No hay empleados activos, podemos marcar como finalizado automáticamente
                            servicio_orden.empleado_finalizado = True
                            servicio_orden.fecha_finalizacion_empleado = timezone.now()
                            servicio_orden.save(update_fields=['empleado_finalizado', 'fecha_finalizacion_empleado'])
                            continue
                        
                        # Tiene empleados activos pero no está finalizado
                        # Verificar si hay registros en curso o pausados
                        registro_activo = RegistroTiempoReal.objects.filter(
                            servicio_orden=servicio_orden,
                            estado__in=['en_curso', 'pausado']
                        ).first()
                        
                        if registro_activo:
                            servicios_no_finalizados.append({
                                'nombre': servicio_orden.servicio.nombre,
                                'estado': registro_activo.estado
                            })
                        else:
                            servicios_no_finalizados.append({
                                'nombre': servicio_orden.servicio.nombre,
                                'estado': 'no_iniciado'
                            })
                    
                    if servicios_no_finalizados:
                        if origen == 'lista':
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return JsonResponse({
                                    'success': False,
                                    'error': 'servicios_pendientes',
                                    'servicios_pendientes': servicios_no_finalizados,
                                    'mensaje': 'No se puede completar la orden porque hay servicios pendientes'
                                })
                            messages.error(request, "No se puede completar la orden. Hay servicios pendientes")
                            return redirect("orden_trabajo_cambiar_estados")
                        
                        messages.error(request, "No se puede completar la orden. Hay servicios pendientes")
                        return redirect("orden_trabajo_ver", orden_id=ot.id)

                except Exception as e:
                    if origen == 'lista':
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'error': 'exception',
                                'mensaje': str(e)
                            })
                        messages.error(request, str(e))
                        return redirect("orden_trabajo_cambiar_estados")
                    messages.error(request, str(e))
                    return redirect("orden_trabajo_ver", orden_id=ot.id)
        
                    
                except Exception as e:
                    if origen == 'lista':
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'error': 'exception',
                                'mensaje': str(e)
                            })
                        messages.error(request, str(e))
                        return redirect("orden_trabajo_cambiar_estados")
                    messages.error(request, str(e))
                    return redirect("orden_trabajo_ver", orden_id=ot.id)
            
            # Continuar con el cambio de estado normal
            ot.estado = nuevo_estado
            
            if nuevo_estado == 'en_proceso' and not ot.fecha_inicio:
                ot.fecha_inicio = timezone.now()
            if nuevo_estado in ['completado', 'cancelado'] and not ot.fecha_fin:
                ot.fecha_fin = timezone.now()
                
            ot.save(update_fields=["estado", "fecha_inicio", "fecha_fin"])

            BitacoraOrden.registrar(ot, _("Cambio de estado"), f"{estado_anterior} → {nuevo_estado}", request.user)
            messages.success(request, f"Orden #{ot.id} {ot.get_estado_display().upper()}")

            if origen == 'lista':
                return redirect("orden_trabajo_cambiar_estados")
            return redirect("orden_trabajo_ver", orden_id=ot.id)
        else:
            messages.error(request, "Estado no válido")
            if origen == 'lista':
                return redirect("orden_trabajo_cambiar_estados")

    return redirect("orden_trabajo_ver", orden_id=ot.id)


@login_required
@permission_required('seguridad.cambiar_estado_ordenes_trabajo', raise_exception=True)
def orden_trabajo_cambiar_estados(request):
    qs = OrdenTrabajo.objects.filter(
        estado__in=['pendiente', 'en_proceso', 'espera_repuestos', 'pausado', 'completado']
    ).select_related('cliente', 'vehiculo')
    
    q = (request.GET.get("q") or "").strip()
    if q:
        # Si el query es numérico, buscar por ID exacto primero
        if q.isdigit():
            qs = qs.filter(
                Q(id=int(q)) | 
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

    paginator = Paginator(qs.order_by("-fecha_creacion"), 10)
    page = request.GET.get("page")
    ordenes = paginator.get_page(page)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    return render(request, "orden_trabajo/orden_trabajo_cambiar_estados.html", {
        "ordenes": ordenes,
        "qs_no_page": qs_no_page,
    })


@login_required
@permission_required('seguridad.imprimir_ordenes_trabajo', raise_exception=True)
def orden_trabajo_imprimir(request, orden_id):
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    servicios = ot.ordenservicio_set.select_related('servicio').order_by('servicio__nombre')
    
    # Obtener asignaciones con conteo de servicios por empleado
    asignaciones_con_contador = []
    for asignacion in ot.asignaciones.select_related('empleado').order_by('empleado__nombre'):
        # Contar cuántos servicios tiene asignado este empleado en esta orden
        servicios_count = AsignacionOrden.objects.filter(
            orden=ot,
            empleado=asignacion.empleado
        ).count()
        
        asignaciones_con_contador.append({
            'asignacion': asignacion,
            'servicios_count': servicios_count
        })

    return render(request, "orden_trabajo/orden_trabajo_imprimir.html", {
        "orden": ot,
        "servicios": servicios,
        "asignaciones_con_contador": asignaciones_con_contador 
    })


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def orden_trabajo_editar_reanudado(request, orden_id):
    """
    Vista específica para editar una orden REANUDADA después de ser rechazada.
    SOLO permite modificar los servicios que fueron RECHAZADOS.
    Los servicios aprobados son SOLO LECTURA.
    """
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    
    # Verificar que la orden esté en estado 'rechazado'
    if ot.estado != 'rechazado':
        messages.error(request, "Solo se pueden reanudar órdenes RECHAZADAS")
        return redirect("orden_trabajo_ver", orden_id=ot.id)
    
    # Obtener IDs de servicios rechazados
    servicios_rechazados_ids = list(ot.servicios_rechazados)
    
    if not servicios_rechazados_ids:
        messages.info(request, "No hay servicios rechazados para modificar")
        return redirect("orden_trabajo_ver", orden_id=ot.id)
    
    # Obtener servicios con información de si son editables
    servicios_con_info = []
    for servicio_orden in ot.ordenservicio_set.select_related('servicio').all():
        revision = RevisionServicio.objects.filter(
            orden_servicio=servicio_orden,
            orden_trabajo=ot
        ).order_by('-fecha_revision').first()
        
        puede_editarse = servicio_orden.id in servicios_rechazados_ids
        servicios_con_info.append({
            'servicio_orden': servicio_orden,
            'puede_editarse': puede_editarse,
            'observacion_revision': revision.observacion if revision else '',
            'aprobado': revision.aprobado if revision else None
        })
    
    # Procesar POST
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Procesar modificaciones SOLO en servicios rechazados
                for servicio_info in servicios_con_info:
                    if not servicio_info['puede_editarse']:
                        continue  # Saltar servicios aprobados
                    
                    servicio_orden = servicio_info['servicio_orden']
                    
                    # Actualizar cantidad si se modificó
                    cantidad_key = f'cantidad_{servicio_orden.id}'
                    if cantidad_key in request.POST:
                        nueva_cantidad = request.POST.get(cantidad_key)
                        if nueva_cantidad:
                            try:
                                nueva_cantidad_dec = Decimal(nueva_cantidad.replace(',', '.'))
                                if nueva_cantidad_dec != servicio_orden.cantidad:
                                    servicio_orden.cantidad = nueva_cantidad_dec
                                    servicio_orden.save(update_fields=['cantidad'])
                            except:
                                pass
                    
                    # Procesar empleados eliminados
                    empleados_eliminados = request.POST.getlist(f'empleados_eliminados_{servicio_orden.id}[]')
                    if empleados_eliminados:
                        AsignacionOrden.objects.filter(
                            servicio=servicio_orden,
                            empleado_id__in=empleados_eliminados
                        ).delete()
                    
                    # Procesar nuevos empleados
                    nuevos_empleados = request.POST.getlist(f'nuevos_empleados_{servicio_orden.id}[]')
                    for emp_id in nuevos_empleados:
                        if emp_id:
                            empleado = get_object_or_404(Empleado, pk=emp_id)
                            if not AsignacionOrden.objects.filter(
                                servicio=servicio_orden,
                                empleado=empleado
                            ).exists():
                                AsignacionOrden.objects.create(
                                    orden=ot,
                                    empleado=empleado,
                                    servicio=servicio_orden,
                                    estado='asignado'
                                )
                    
                    # Resetear el estado del servicio rechazado
                    # para que los empleados puedan trabajarlo de nuevo
                    if servicio_orden.empleado_finalizado:
                        servicio_orden.empleado_finalizado = False
                        servicio_orden.fecha_finalizacion_empleado = None
                        servicio_orden.save(update_fields=['empleado_finalizado', 'fecha_finalizacion_empleado'])
                    
                    # Resetear las asignaciones de empleados para este servicio
                    # Las asignaciones existentes están en estado 'liberado', las cambiamos a 'asignado'
                    AsignacionOrden.objects.filter(
                        servicio=servicio_orden,
                        estado='liberado'
                    ).update(estado='asignado', fecha_liberacion=None)
                    
                    # Eliminar registros de tiempo de este servicio para que empiecen de cero
                    RegistroTiempoReal.objects.filter(
                        servicio_orden=servicio_orden
                    ).delete()
                
                # Cambiar estado de la orden a en_proceso
                ot.estado = 'en_proceso'
                ot.save(update_fields=['estado'])
                
                # Actualizar totales
                ot.actualizar_totales(save=True)
                
                BitacoraOrden.registrar(
                    ot, 
                    "Orden reanudada después de rechazo", 
                    f"Se reanudaron {len(servicios_rechazados_ids)} servicio(s) rechazado(s)", 
                    request.user
                )
                
                messages.success(
                    request, 
                    f"Orden #{ot.id} reanudada correctamente. Los servicios rechazados ahora están disponibles para trabajar."
                )
                return redirect("orden_trabajo_ver", orden_id=ot.id)
                
        except Exception as e:
            messages.error(request, f"Error al guardar: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # GET - mostrar formulario
    servicios_disponibles = Servicio.objects.filter(is_active=True)
    empleados_disponibles = Empleado.objects.filter(estado=True).order_by('nombre')
    
    return render(request, "orden_trabajo/orden_trabajo_editar_reanudado.html", {
        "orden": ot,
        "servicios_con_info": servicios_con_info,
        "servicios_rechazados_ids": servicios_rechazados_ids,
        "servicios_disponibles": servicios_disponibles,
        "empleados_disponibles": empleados_disponibles,
    })


# GENERAR FACTURA (PRECARGAR DATOS)
@permission_required('seguridad.agregar_facturas', raise_exception=True)
def generar_factura_desde_orden(request, orden_id):
    """
    Vista para precargar datos en el formulario de factura
    """
    orden = get_object_or_404(OrdenTrabajo, id=orden_id)
    
    # Solo de ordenes aprobadas
    if orden.estado != 'aprobado':
        messages.error(request, "Solo se pueden generar facturas desde órdenes de trabajo APROBADAS")
        return redirect('orden_trabajo_lista')
    
    # VERIFICAR SI YA EXISTE UNA FACTURA
    if orden.factura_generada:
        messages.error(request, "Ya se generó una factura desde esta orden de trabajo")
        return redirect('orden_trabajo_lista')
    
    # Redirigir a la creación de factura
    response = redirect('factura_emitir')
    response['Location'] += f'?orden_id={orden_id}'
    return response


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def orden_servicio_finalizar(request, servicio_id):
    """
    Vista para que un empleado marque un servicio como finalizado.
    """
    if request.method != 'POST':
        return redirect('orden_trabajo_lista')
    
    try:
        from .services import ComisionService
        
        # Obtener el servicio de orden
        orden_servicio = get_object_or_404(
            OrdenServicio.objects.select_related('orden', 'servicio'),
            pk=servicio_id
        )
        
        # Verificar que la orden esté en proceso
        if orden_servicio.orden.estado != 'en_proceso':
            messages.error(request, "Solo se pueden finalizar servicios en órdenes 'En Proceso'")
            return redirect('orden_trabajo_ver', orden_id=orden_servicio.orden.id)
        
        # Si ya está finalizado, no hacer nada
        if orden_servicio.empleado_finalizado:
            messages.info(request, "Este servicio ya fue marcado como finalizado")
            return redirect('orden_trabajo_ver', orden_id=orden_servicio.orden.id)
        
        # Verificar si tiene empleados asignados
        asignaciones = orden_servicio.asignacionorden_set.filter(
            estado__in=['asignado', 'en_ejecucion']
        )
        
        if not asignaciones.exists():
            messages.error(request, "No hay empleados activos asignados a este servicio")
            return redirect('orden_trabajo_ver', orden_id=orden_servicio.orden.id)
        
        # Usar el primer empleado o None para que el servicio maneje todas las asignaciones
        # No necesitamos pasar un empleado específico, el servicio liberará todas las asignaciones
        success, message = ComisionService.procesar_finalizacion_servicio(
            orden_servicio_id=servicio_id,
            empleado_id=None  
        )
        
        if success:
            messages.success(request, f"Servicio '{orden_servicio.servicio.nombre}' marcado como finalizado")
        else:
            messages.error(request, f"Error: {message}")
        
    except OrdenServicio.DoesNotExist:
        messages.error(request, "Servicio no encontrado")
        return redirect('orden_trabajo_lista')
    except Exception as e:
        messages.error(request, f"Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'orden_servicio' in locals():
            return redirect('orden_trabajo_ver', orden_id=orden_servicio.orden.id)
        return redirect('orden_trabajo_lista')
    
    return redirect('orden_trabajo_ver', orden_id=orden_servicio.orden.id)


# ========================
# ASIGNACIONES (EMPLEADOS)
# ========================

@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def asignar_empleado(request, orden_id):
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    if request.method != "POST":
        return redirect("orden_trabajo_ver", orden_id=ot.id)

    form = AsignacionOrdenForm(request.POST, orden=ot)  
    if not form.is_valid():
        messages.error(request, "Revisá los datos del formulario de asignación")
        return redirect("orden_trabajo_ver", orden_id=ot.id)

    asignacion = form.save(commit=False)
    asignacion.orden = ot

    abiertas = AsignacionOrden.objects.filter(
        empleado=asignacion.empleado,
        estado__in=['asignado', 'en_ejecucion'],
        orden__estado__in=['pendiente', 'en_proceso']
    ).exclude(orden=ot)

    bloquear = str(ConfiguracionSistema.get_valor(
        "orden_trabajo.bloquear_asignacion_si_tiene_ot_abierta", "False"
    )).strip().lower() in ("1", "true", "t", "yes", "si", "sí")

    if abiertas.exists() and bloquear:
        listado = ", ".join(f"#{a.orden_id}" for a in abiertas[:5])
        messages.error(
            request,
            f"El empleado {asignacion.empleado} tiene {abiertas.count()} OT(s) abierta(s): {listado}. "
            "La política actual impide nuevas asignaciones."
        )
        return redirect("orden_trabajo_ver", orden_id=ot.id)

    asignacion.save()
    BitacoraOrden.registrar(ot, _("Asignación de empleado"), f"Empleado: {asignacion.empleado}", request.user)

    if abiertas.exists() and not bloquear:
        listado = ", ".join(f"#{a.orden_id}" for a in abiertas[:5])
        messages.warning(
            request,
            f"{asignacion.empleado} ya tiene {abiertas.count()} OT(s) abierta(s): {listado}."
        )
    else:
        messages.success(request, f"Empleado {asignacion.empleado} asignado")

    return redirect("orden_trabajo_ver", orden_id=ot.id)


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def liberar_empleado(request, orden_id, asignacion_id):
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    asignacion = get_object_or_404(AsignacionOrden, pk=asignacion_id, orden=ot)

    if asignacion.estado != 'liberado':
        asignacion.estado = 'liberado'
        asignacion.fecha_liberacion = timezone.now()
        asignacion.save(update_fields=["estado", "fecha_liberacion"])
        BitacoraOrden.registrar(ot, _("Liberación de empleado"), f"Empleado: {asignacion.empleado}", request.user)
        messages.success(request, "Empleado liberado")
    else:
        messages.info(request, "La asignación ya estaba liberada")

    return redirect("orden_trabajo_ver", orden_id=ot.id)


##
@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def agregar_empleado_ot(request, ot_id):
    """Vista para agregar empleado a una orden de trabajo"""
    if request.method == 'POST':
        try:
            orden = get_object_or_404(OrdenTrabajo, pk=ot_id)
            empleado_id = request.POST.get('empleado_id')
            servicio_id = request.POST.get('servicio_id')
            
            if not empleado_id or not servicio_id:
                messages.error(request, "Faltan datos requeridos")
                return redirect('orden_trabajo_editar', orden_id=ot_id)
            
            empleado = get_object_or_404(Empleado, pk=empleado_id)
            servicio = get_object_or_404(Servicio, pk=servicio_id)
            tiempo_minutos = servicio.tiempo_min_estimado or 0
            
            # Registrar tiempo y verificar carga
            registro, estado_carga = ControlCargaService.registrar_tiempo_empleado(
                empleado, orden, servicio, tiempo_minutos 
            )
            
            # Mostrar alerta si está sobrecargado
            if estado_carga['sobrecargado']:
                messages.warning(request, 
                    f"ALERTA: {empleado.nombre} está sobrecargado. "
                    f"Tiempo actual: {estado_carga['total_horas']:.1f}h "
                    f"Límite: {empleado.limite_horas_diarias}h"
                )
            elif estado_carga['nivel_alerta'] == 'advertencia':
                messages.warning(request, estado_carga['mensaje'])
            elif estado_carga['nivel_alerta'] == 'info':
                messages.info(request, estado_carga['mensaje'])
            
            messages.success(request, f"Empleado {empleado.nombre} agregado correctamente")
            
        except Exception as e:
            messages.error(request, f"Error al agregar empleado: {str(e)}")
        
        return redirect('orden_trabajo_editar', orden_id=ot_id)
    
    return redirect('orden_trabajo_editar', orden_id=ot_id)


@login_required
@permission_required('seguridad.ver_ordenes_trabajo', raise_exception=True)
def empleado_ordenes(request, empleado_id):
    """Vista para listar las órdenes de trabajo asociadas a un empleado"""
    from decimal import Decimal, ROUND_UP
    
    empleado = get_object_or_404(Empleado, pk=empleado_id)

    # Obtener estado de carga del empleado
    estado_carga = ControlCargaService.verificar_estado_carga(empleado)

    # Obtener filtros
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    # órdenes donde el empleado tiene asignaciones
    qs = OrdenTrabajo.objects.filter(
        asignaciones__empleado=empleado
    ).select_related('cliente', 'vehiculo').distinct()

    # Aplicar filtros
    if q:
        if q.isdigit():
            qs = qs.filter(
                Q(id=int(q)) |
                Q(cliente__nombre__icontains=q) |
                Q(vehiculo__nro_chapa__icontains=q) |
                Q(vehiculo__nro_chasis__icontains=q) |
                Q(vehiculo__marca__icontains=q) |
                Q(vehiculo__modelo__icontains=q)
            )
        else:
            qs = qs.filter(
                Q(cliente__nombre__icontains=q) |
                Q(vehiculo__nro_chapa__icontains=q) |
                Q(vehiculo__nro_chasis__icontains=q) |
                Q(vehiculo__marca__icontains=q) |
                Q(vehiculo__modelo__icontains=q)
            )
    
    if estado:
        qs = qs.filter(estado=estado)
    
    if fecha_desde:
        qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
    
    if fecha_hasta:
        qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

    # Ordenar por fecha más reciente
    qs = qs.order_by("-fecha_creacion")

    # Paginación
    paginator = Paginator(qs, 10)
    page = request.GET.get("page")
    ordenes = paginator.get_page(page)

    # Mantener parámetros GET para paginación
    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    # ========== CALCULAR ESTADO DEL EMPLEADO PARA CADA ORDEN ==========
    def redondear_arriba(valor):
        if valor is None:
            return Decimal('0')
        return valor.quantize(Decimal('1'), rounding=ROUND_UP)
    
    for orden in ordenes:
        orden.comision_empleado = Decimal('0')
        orden.porcentaje_comision = None
        orden.estado_empleado = None
        orden.tiempo_trabajado = None
        orden.servicio_trabajando = None
        
        # Buscar asignación de ESTE empleado específico en esta orden
        asignacion = AsignacionOrden.objects.filter(
            orden=orden,
            empleado=empleado
        ).select_related('registro_tiempo_real', 'servicio__servicio').first()

        # Calcular si la comisión es compartida
        orden.compartido = False
        orden.cantidad_empleados = 0

        # Buscar si hay servicios con múltiples empleados
        for servicio_orden in orden.ordenservicio_set.all():
            total_emp_servicio = AsignacionOrden.objects.filter(
                orden=orden,
                servicio=servicio_orden
            ).count()
            
            if total_emp_servicio > 1:
                orden.compartido = True
                orden.cantidad_empleados = total_emp_servicio
                break  # Solo necesitamos saber si hay al menos uno compartido

        if asignacion:
            # ===== CALCULAR COMISIÓN POTENCIAL (para mostrar, NO suma aún) =====
            # Mostrar para todas las órdenes que NO están canceladas
            if orden.estado not in ['cancelado']:
                comision_total = Decimal('0')
                porcentaje_mostrar = Decimal('0')
                
                # Obtener TODAS las asignaciones de este empleado en esta orden
                todas_asignaciones = AsignacionOrden.objects.filter(
                    orden=orden,
                    empleado=empleado,
                    servicio__isnull=False
                ).select_related('servicio__servicio')
                
                for asig in todas_asignaciones:
                    servicio_orden = asig.servicio
                    if servicio_orden and servicio_orden.servicio.comision_porcentaje:
                        porcentaje = servicio_orden.servicio.comision_porcentaje
                        # Usar el subtotal del servicio (cantidad * precio_unitario)
                        subtotal = servicio_orden.subtotal
                        comision = (subtotal * porcentaje) / Decimal('100')
                        comision_total += comision.quantize(Decimal('1'), rounding=ROUND_UP)
                        porcentaje_mostrar = porcentaje  # Guardar el porcentaje para mostrar
                
                orden.comision_empleado = comision_total
                if comision_total > 0:
                    orden.porcentaje_comision = porcentaje_mostrar
            
            # ===== ESTADO DEL EMPLEADO (INDIVIDUAL) =====
            if asignacion.registro_tiempo_real:
                registro = asignacion.registro_tiempo_real
                orden.estado_empleado = registro.estado
                orden.tiempo_trabajado = registro.tiempo_formateado
                if registro.servicio_orden:
                    orden.servicio_trabajando = registro.servicio_orden.servicio.nombre
            elif asignacion.estado == 'liberado':
                orden.estado_empleado = 'finalizado'
                orden.tiempo_trabajado = "Completado"
            else:
                orden.estado_empleado = 'no_iniciado'
        else:
            orden.estado_empleado = 'sin_asignacion'

    # Estadísticas
    todas_ordenes = OrdenTrabajo.objects.filter(asignaciones__empleado=empleado).distinct()
    total_ordenes = todas_ordenes.count()
    ordenes_pendientes = todas_ordenes.filter(estado__in=['pendiente', 'en_proceso', 'espera_repuestos', 'pausado']).count()
    ordenes_completadas = todas_ordenes.filter(estado__in=['completado', 'facturado']).count()
    ordenes_canceladas = todas_ordenes.filter(estado='cancelado').count()
    total_facturado = todas_ordenes.filter(estado='facturado').aggregate(total=models.Sum('total'))['total'] or 0

    # Comisiones
    comision_acumulada = redondear_arriba(empleado.comision_acumulada)
    comision_por_cobrar = redondear_arriba(empleado.comision_por_cobrar)

    return render(request, "empleado/empleado_ordenes.html", {
        "empleado": empleado,
        "estado_carga": estado_carga,
        "ordenes": ordenes,
        "qs_no_page": qs_no_page,
        "estados": ESTADOS_ORDEN,
        "total_ordenes": total_ordenes,
        "ordenes_pendientes": ordenes_pendientes,
        "ordenes_completadas": ordenes_completadas,
        "ordenes_canceladas": ordenes_canceladas,
        "total_facturado": total_facturado,
        "comision_acumulada": comision_acumulada,
        "comision_por_cobrar": comision_por_cobrar,
    })


# ========================
# GESTIÓN DE COMISIONES
# ========================

@login_required
@permission_required('seguridad.gestionar_empleados', raise_exception=True)
def pagar_comision_empleado(request, empleado_id):
    """Pagar las comisiones por cobrar de un empleado (Cerrar Semana)"""
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    
    if request.method == 'POST':
        monto_pagado = empleado.comision_por_cobrar or Decimal('0')
        
        # Sumar a comisión acumulada (historial)
        empleado.comision_acumulada += monto_pagado
        # REINICIAR comisión por cobrar a CERO
        empleado.comision_por_cobrar = Decimal('0')
        empleado.save(update_fields=['comision_acumulada', 'comision_por_cobrar'])
        
        messages.success(
            request, 
            f"Se pagaron ₲ {monto_pagado:,.0f} en comisiones a {empleado.nombre}"
        )
        
        return redirect('empleado_ordenes', empleado_id=empleado.id_empleado)
    
    return redirect('empleado_ordenes', empleado_id=empleado.id_empleado)


@login_required
@permission_required('seguridad.ver_empleados', raise_exception=True)
def empleado_comisiones_historial(request, empleado_id):
    """
    Vista para ver el historial de comisiones pagadas a un empleado.
    """
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    
    # Aquí necesitarías un modelo PagoComision para almacenar el historial
    # Por ahora, solo mostramos las órdenes completadas con sus comisiones
    
    # Obtener órdenes completadas/facturadas del empleado
    ordenes_completadas = OrdenTrabajo.objects.filter(
        asignaciones__empleado=empleado,
        estado__in=['completado', 'facturado']
    ).distinct().order_by('-fecha_creacion')
    
    # Calcular comisión por orden
    comisiones_por_orden = []
    total_comisiones = Decimal('0')
    
    for orden in ordenes_completadas:
        comision_orden = Decimal('0')
        asignaciones = AsignacionOrden.objects.filter(
            orden=orden,
            empleado=empleado
        ).select_related('servicio__servicio')
        
        for asignacion in asignaciones:
            if asignacion.servicio and asignacion.servicio.servicio.comision_porcentaje:
                porcentaje = asignacion.servicio.servicio.comision_porcentaje
                subtotal = asignacion.servicio.subtotal
                comision = (subtotal * porcentaje) / Decimal('100')
                comision_orden += comision
        
        if comision_orden > 0:
            comisiones_por_orden.append({
                'orden': orden,
                'comision': comision_orden,
                'fecha': orden.fecha_fin or orden.fecha_creacion
            })
            total_comisiones += comision_orden
    
    return render(request, "empleado/empleado_comisiones.html", {
        "empleado": empleado,
        "comisiones": comisiones_por_orden,
        "total_comisiones": total_comisiones,
        "comision_acumulada": empleado.comision_acumulada,
    })


# ========================
# GESTIÓN DE TIEMPO REAL
# ========================

@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def iniciar_trabajo_empleado(request, orden_id, servicio_orden_id):
    from .services import TiempoRealService
    
    if request.method != 'POST':
        return redirect('orden_trabajo_cambiar_estados')
    
    try:
        orden = get_object_or_404(OrdenTrabajo, pk=orden_id)
        servicio_orden = get_object_or_404(OrdenServicio, pk=servicio_orden_id, orden=orden)
        
        # Obtener el empleado
        empleado_id = request.POST.get('empleado_id')
        if not empleado_id:
            asignacion = servicio_orden.asignacionorden_set.filter(
                estado__in=['asignado', 'en_ejecucion']
            ).first()
            if asignacion:
                empleado_id = asignacion.empleado.id_empleado
        
        empleado = get_object_or_404(Empleado, id_empleado=empleado_id)
        
        # SI LA ORDEN ESTÁ PENDIENTE, LA CAMBIAMOS A EN PROCESO
        if orden.estado == 'pendiente':
            orden.estado = 'en_proceso'
            if not orden.fecha_inicio:
                orden.fecha_inicio = timezone.now()
            orden.save(update_fields=['estado', 'fecha_inicio'])
            messages.info(request, f"Orden #{orden.id} marcada como EN PROCESO")
        
        # Verificar que el empleado esté asignado
        asignacion_existe = AsignacionOrden.objects.filter(
            orden=orden,
            servicio=servicio_orden,
            empleado=empleado,
            estado__in=['asignado', 'en_ejecucion']
        ).exists()
        
        if not asignacion_existe:
            messages.error(request, "Este empleado no está asignado a este servicio")
            return redirect('orden_trabajo_cambiar_estados')
        
        # Iniciar trabajo
        registro, success, message = TiempoRealService.iniciar_trabajo(
            empleado=empleado,
            orden_trabajo=orden,
            servicio_orden=servicio_orden
        )
        
        if success:
            messages.success(request, f"Trabajo iniciado para {empleado.nombre} en OT #{orden.id}")
        else:
            messages.error(request, message)
        
    except Exception as e:
        messages.error(request, f"Error al iniciar trabajo: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return redirect('orden_trabajo_cambiar_estados')


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def finalizar_trabajo_empleado(request, registro_id):
    """Vista para finalizar el registro de tiempo real de un empleado."""
    
    if request.method != 'POST':
        return redirect('orden_trabajo_cambiar_estados')
    
    try:
        registro = get_object_or_404(RegistroTiempoReal, pk=registro_id)
        orden = registro.orden_trabajo
        empleado = registro.empleado
        servicio_orden = registro.servicio_orden
        
        # ===== No se puede finalizar si está pausado =====
        if registro.estado == 'pausado':
            messages.error(request, "No se puede finalizar un trabajo que está PAUSADO. Primero debe reanudarlo")
            return redirect('orden_trabajo_cambiar_estados')
        
        if registro.estado == 'finalizado':
            messages.warning(request, "Este trabajo ya estaba finalizado")
            return redirect('orden_trabajo_cambiar_estados')
        
        # ===== VERIFICAR SI EL SERVICIO YA ESTÁ COMPLETADO =====
        if servicio_orden and servicio_orden.empleado_finalizado:
            messages.warning(request, f"El servicio '{servicio_orden.servicio.nombre}' ya estaba completado")
            # Aún así, finalizar el registro de tiempo
            registro, success, message = TiempoRealService.finalizar_trabajo(registro_id)
            return redirect('orden_trabajo_cambiar_estados')
        
        # ===== FINALIZAR EL REGISTRO DE TIEMPO DEL EMPLEADO =====
        registro, success, message = TiempoRealService.finalizar_trabajo(registro_id)
        
        if not success:
            messages.error(request, message)
            return redirect('orden_trabajo_cambiar_estados')
        
        if "excedió" in message:
            messages.warning(request, message)
        else:
            messages.success(request, message)
        
        # ===== PROCESAR FINALIZACIÓN DEL SERVICIO =====
        # SOLO si el servicio NO está completado aún
        if servicio_orden and not servicio_orden.empleado_finalizado:
            from .services import ComisionService
            
            success, mensaje_final = ComisionService.procesar_finalizacion_servicio(
                servicio_orden.id, 
                empleado_id=empleado.id_empleado,
                usuario=request.user
            )
            
            if success:
                if "completado" in mensaje_final.lower():
                    messages.success(request, mensaje_final)
                else:
                    messages.info(request, mensaje_final)
            else:
                messages.error(request, mensaje_final)
                return redirect('orden_trabajo_cambiar_estados')
        
        # Verificar si la orden se completó automáticamente
        orden_servicios = orden.ordenservicio_set.all()
        todos_finalizados = all(s.empleado_finalizado for s in orden_servicios)
        
        if todos_finalizados and orden.estado == 'en_proceso':
            orden.estado = 'completado'
            orden.fecha_fin = timezone.now()
            orden.save(update_fields=['estado', 'fecha_fin'])
            
            BitacoraOrden.registrar(
                orden,
                "Completado automático",
                f"Todos los servicios fueron completados. Último empleado: {empleado.nombre}",
                request.user
            )
            messages.success(request, f"Orden #{orden.id} completada automáticamente")
        
    except Exception as e:
        messages.error(request, f"Error al finalizar trabajo: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return redirect('orden_trabajo_cambiar_estados')


@login_required
def obtener_tiempo_real_empleado(request, empleado_id):
    """
    API para obtener el tiempo real trabajado hoy por un empleado.
    """
    from .services import TiempoRealService
    
    empleado = get_object_or_404(Empleado, id_empleado=empleado_id)
    minutos_totales = TiempoRealService.obtener_tiempo_empleado_hoy(empleado)
    
    return JsonResponse({
        'minutos': minutos_totales,
        'horas': minutos_totales / 60,
        'horas_formateadas': TiempoRealService.minutos_a_hhmm(minutos_totales)
    })
                            

@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def pausar_trabajo_empleado(request, registro_id):
    """
    Pausa el trabajo de un empleado.
    SOLO se puede pausar si está 'en_curso'
    """
    from .services import TiempoRealService
    from .models import RegistroTiempoReal
    
    if request.method != 'POST':
        return redirect('orden_trabajo_cambiar_estados')
    
    try:
        registro = get_object_or_404(RegistroTiempoReal, pk=registro_id)
        orden_id = registro.orden_trabajo.id
        
        # ===== No se puede pausar si ya está pausado =====
        if registro.estado == 'pausado':
            messages.warning(request, "El trabajo ya estaba pausado")
            return redirect('orden_trabajo_cambiar_estados')
        
        if registro.estado == 'finalizado':
            messages.error(request, "No se puede pausar un trabajo ya finalizado")
            return redirect('orden_trabajo_cambiar_estados')
        
        registro, success, message = TiempoRealService.pausar_trabajo(registro_id)
        
        if success:
            messages.info(request, message)
        else:
            messages.error(request, message)
        
    except Exception as e:
        messages.error(request, f"Error al pausar trabajo: {str(e)}")
    
    return redirect('orden_trabajo_cambiar_estados')


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def reanudar_trabajo_empleado(request, registro_id):
    from .services import TiempoRealService
    from .models import RegistroTiempoReal
    
    if request.method != 'POST':
        return redirect('orden_trabajo_cambiar_estados')
    
    try:
        registro = get_object_or_404(RegistroTiempoReal, pk=registro_id)
        orden = registro.orden_trabajo
        
        # Verificar si hay trabajo en curso en otro servicio diferente
        servicio_en_curso = TiempoRealService.obtener_servicio_en_curso(orden)
        if servicio_en_curso and servicio_en_curso.id != registro.servicio_orden.id:
            messages.error(request, f"No se puede reanudar. Hay empleados trabajando en otro servicio.")
            return redirect('orden_trabajo_cambiar_estados')
        
        registro, success, message = TiempoRealService.reanudar_trabajo(registro_id)
        
        if success:
            registro.refresh_from_db()
            messages.success(request, message)
        else:
            messages.error(request, message)
        
    except Exception as e:
        messages.error(request, f"Error al reanudar trabajo: {str(e)}")
    
    return redirect('orden_trabajo_cambiar_estados')



@login_required
def limpiar_todo_tiempo(request):
    """Vista TEMPORAL para limpiar todos los registros de tiempo"""
    if not request.user.is_superuser:
        messages.error(request, "Solo administradores")
        return redirect('orden_trabajo_cambiar_estados')
    
    from .models import RegistroTiempoReal
    count = RegistroTiempoReal.objects.all().count()
    RegistroTiempoReal.objects.all().delete()
    messages.success(request, f"Se eliminaron {count} registros de tiempo")
    return redirect('orden_trabajo_cambiar_estados')


# BÚSQUEDAS
@login_required
def buscar_clientes_autocomplete(request):
    """Vista para autocompletar clientes """
    query = request.GET.get('q', '')
    
    try:     
        if query:
            # Buscar por documento o nombre
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
    """Vista para autocompletar vehículos - IDÉNTICA A PRESUPUESTOS"""
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


# ========
# REVISIÓN
# ========

@login_required
@permission_required('seguridad.cambiar_estado_ordenes_trabajo', raise_exception=True)
def orden_enviar_revision(request, orden_id):
    """Envía una orden completada a revisión"""
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    
    # Aceptar tanto GET como POST
    if request.method in ["POST", "GET"]:
        try:
            # Cambiar el estado a en_revision (sin crear revisiones aún)
            ot.cambiar_estado('en_revision')
            messages.success(request, f"Orden #{ot.id} enviada a REVISIÓN")
            BitacoraOrden.registrar(ot, "Envío a revisión", "Orden enviada para control de calidad", request.user)
            return redirect("orden_revision", orden_id=ot.id)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("orden_trabajo_ver", orden_id=ot.id)
    
    return redirect("orden_trabajo_ver", orden_id=ot.id)


@login_required
@permission_required('seguridad.cambiar_estado_ordenes_trabajo', raise_exception=True)
def orden_revision(request, orden_id):
    """Vista para revisar los servicios de una orden"""
    ot = get_object_or_404(OrdenTrabajo.objects.prefetch_related(
        'ordenservicio_set__servicio',
        'ordenservicio_set__revisiones'
    ), pk=orden_id)
    
    if ot.estado != 'en_revision':
        messages.error(request, "Esta orden no está en estado de revisión")
        return redirect("orden_trabajo_ver", orden_id=ot.id)
    
    # Obtener servicios con sus estados de revisión
    servicios_con_revision = []
    for servicio_orden in ot.ordenservicio_set.all():
        revision = RevisionServicio.objects.filter(
            orden_servicio=servicio_orden,
            orden_trabajo=ot
        ).first()
        
        # IMPORTANTE: Si no hay revisión, el estado es None (sin marcar)
        # No forzar a False
        estado_aprobado = None
        if revision:
            estado_aprobado = revision.aprobado
        
        servicios_con_revision.append({
            'servicio_orden': servicio_orden,
            'revision': revision,
            'aprobado': estado_aprobado  # Puede ser True, False o None
        })
    
    if request.method == "POST":
        # Procesar cada servicio individualmente
        for servicio_orden in ot.ordenservicio_set.all():
            estado_key = f'estado_{servicio_orden.id}'
            observacion_key = f'observaciones_{servicio_orden.id}'
            
            if estado_key in request.POST:
                decision = request.POST.get(estado_key)
                observacion = request.POST.get(observacion_key, '')
                
                if decision == 'aprobado':
                    ot.aprobar_servicio(servicio_orden.id, request.user, observacion)
                elif decision == 'rechazado':
                    ot.rechazar_servicio(servicio_orden.id, request.user, observacion)
        
        # Verificar el estado actual de los servicios después de guardar
        revisiones = RevisionServicio.objects.filter(orden_trabajo=ot)
        hay_rechazados = revisiones.filter(aprobado=False).exists()
        todos_aprobados = revisiones.exists() and not hay_rechazados and revisiones.count() == ot.ordenservicio_set.count()
        
        # Decidir el nuevo estado de la orden
        if todos_aprobados:
            try:
                ot.aprobar_revision(request.user)
                messages.success(request, f"OT #{ot.id} APROBADA")
            except ValidationError as e:
                messages.error(request, str(e))
        elif hay_rechazados:
            try:
                ot.rechazar_revision(request.user)
                messages.error(request, f"OT #{ot.id} RECHAZADA")
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.info(request, "No hay cambios en la revisión.")
        
        return redirect("orden_trabajo_ver", orden_id=ot.id)
    
    # Calcular estado actual para el template
    revisiones = RevisionServicio.objects.filter(orden_trabajo=ot)
    hay_rechazados = revisiones.filter(aprobado=False).exists()
    todos_aprobados = revisiones.exists() and not hay_rechazados and revisiones.count() == ot.ordenservicio_set.count()
    
    return render(request, "orden_trabajo/orden_trabajo_revision.html", {
        "orden": ot,
        "servicios_con_revision": servicios_con_revision,
        "todos_aprobados": todos_aprobados,
        "hay_rechazados": hay_rechazados
    })


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def orden_reanudar_desde_rechazo(request, orden_id):
    """Reanuda una orden rechazada para corregir solo los servicios rechazados"""
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    
    if request.method == "POST":
        if ot.estado != 'rechazado':
            messages.error(request, "Solo se pueden reanudar órdenes en estado RECHAZADO")
            return redirect("orden_trabajo_ver", orden_id=ot.id)
        
        try:
            ot.reanudar_desde_rechazo(request.user)
            messages.success(request, f"Orden #{ot.id} reanudada. Solo se pueden modificar los servicios rechazados")
        except ValidationError as e:
            messages.error(request, str(e))
    
    return redirect("orden_trabajo_ver", orden_id=ot.id)


@login_required
@permission_required('seguridad.editar_ordenes_trabajo', raise_exception=True)
def orden_facturar_desde_aprobado(request, orden_id):
    """Factura una orden aprobada"""
    ot = get_object_or_404(OrdenTrabajo, pk=orden_id)
    
    if ot.estado != 'aprobado':
        messages.error(request, "Solo las órdenes APROBADAS pueden facturarse")
        return redirect("orden_trabajo_ver", orden_id=ot.id)
    
    # Redirigir a la creación de factura con la orden precargada
    response = redirect('factura_emitir')
    response['Location'] += f'?orden_id={orden_id}'
    return response