from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from insumo.models import Insumo

from .forms import ServicioForm, ServicioEditarForm
from .models import Servicio, ServicioInsumo

# =========
# SERVICIOS
# =========

@login_required
@permission_required('seguridad.agregar_servicios', raise_exception=True)
def servicio_crear(request):
    if request.method == "POST":
        form = ServicioForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear servicio sin insumos primero
                    servicio = form.save(commit=False)
                    
                    # Establecer valores por defecto
                    servicio.costo_insumos = Decimal('0.00')
                    
                    # Guardar para obtener ID
                    servicio.save()
                    
                    # Procesar insumos
                    insumos_data = []
                    i = 0
                    while True:
                        insumo_key = f'insumos_nuevos[{i}][insumo_id]'
                        cantidad_key = f'insumos_nuevos[{i}][cantidad]'
                        
                        if insumo_key not in request.POST:
                            break
                            
                        insumo_id = request.POST.get(insumo_key)
                        cantidad = request.POST.get(cantidad_key)
                        
                        if insumo_id and cantidad:
                            insumos_data.append({
                                'insumo_id': insumo_id,
                                'cantidad': cantidad
                            })
                        i += 1
                    
                    # Crear insumos si hay datos
                    insumos_creados = 0
                    for insumo_info in insumos_data:
                        try:
                            insumo = Insumo.objects.get(id=insumo_info['insumo_id'], is_active=True)
                            ServicioInsumo.objects.create(
                                servicio=servicio,
                                insumo=insumo,
                                cantidad=insumo_info['cantidad']
                            )
                            insumos_creados += 1
                        except Insumo.DoesNotExist:
                            continue
                    
                    # Solo actualizar costos si se crearon insumos
                    if insumos_creados > 0:
                        servicio.actualizar_costo_insumos()
                        servicio.save()
                        
                if insumos_creados == 1:
                    messages.success(request, f"Servicio {servicio.nombre} creado con {insumos_creados} insumo")
                else:
                    messages.success(request, f"Servicio {servicio.nombre} creado con {insumos_creados} insumos")
                
                return redirect("servicio_lista") 
                
            except Exception as e:
                messages.error(request, f"Error al crear servicio: {str(e)}")

    else:
        form = ServicioForm()

    insumos_disponibles = Insumo.objects.filter(is_active=True)

    return render(request, "servicio/servicio_crear.html", {  
        "form": form,
        "insumos_disponibles": insumos_disponibles
    })


@login_required
@permission_required('seguridad.ver_servicios', raise_exception=True)
def servicio_ver(request, servicio_id):
    s = get_object_or_404(Servicio, pk=servicio_id)
    insumos_servicio = s.servicioinsumo_set.all().select_related('insumo').order_by('insumo__nombre')
    return render(request, "servicio/servicio_ver.html", {
        "servicio": s,
        "insumos_servicio": insumos_servicio
    })


@login_required
@permission_required('seguridad.editar_servicios', raise_exception=True)
def servicio_editar(request, servicio_id):
    try:
        s = get_object_or_404(Servicio, pk=servicio_id)
        puede_desactivar_servicios = request.user.has_perm('seguridad.desactivar_servicios')
        
        # Obtener insumos del servicio
        insumos_servicio = s.servicioinsumo_set.all().select_related('insumo').order_by('insumo__nombre')
        insumos_disponibles = Insumo.objects.filter(is_active=True)

        if request.method == "POST":
            form = ServicioEditarForm(request.POST, instance=s)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        servicio = form.save()
                        
                        # PROCESAR INSUMOS EXISTENTES (los que vienen del formulario inicial)
                        insumos_existentes_procesados = set()
                        
                        # Recorrer todos los insumos existentes que vienen en el formulario
                        for key, value in request.POST.items():
                            if key.startswith('insumos_existentes[') and '[insumo_id]' in key:
                                # Extraer el ID del insumo del nombre del campo
                                insumo_id = value
                                cantidad_key = key.replace('[insumo_id]', '[cantidad]')
                                cantidad = request.POST.get(cantidad_key, '0')
                                
                                try:
                                    insumo = Insumo.objects.get(id=insumo_id, is_active=True)
                                    cantidad_float = float(cantidad) if cantidad else 0
                                    
                                    if cantidad_float > 0:
                                        # Actualizar la relación servicio-insumo existente
                                        ServicioInsumo.objects.update_or_create(
                                            servicio=servicio,
                                            insumo=insumo,
                                            defaults={'cantidad': cantidad_float}
                                        )
                                        insumos_existentes_procesados.add(insumo_id)
                                except (Insumo.DoesNotExist, ValueError):
                                    pass
                        
                        # PROCESAR NUEVOS INSUMOS
                        counter = 0
                        while True:
                            insumo_id = request.POST.get(f'insumos_nuevos[{counter}][insumo_id]')
                            cantidad = request.POST.get(f'insumos_nuevos[{counter}][cantidad]')
                            
                            if not insumo_id:
                                break
                                
                            try:
                                insumo = Insumo.objects.get(id=insumo_id, is_active=True)
                                cantidad_float = float(cantidad) if cantidad else 0
                                
                                if cantidad_float > 0:
                                    # Crear nueva relación servicio-insumo
                                    ServicioInsumo.objects.update_or_create(
                                        servicio=servicio,
                                        insumo=insumo,
                                        defaults={'cantidad': cantidad_float}
                                    )
                                    insumos_existentes_procesados.add(insumo_id)
                            except (Insumo.DoesNotExist, ValueError):
                                pass
                                
                            counter += 1
                        
                        # ELIMINAR INSUMOS MARCADOS PARA ELIMINACIÓN
                        insumos_eliminados = request.POST.getlist('insumos_eliminados[]')
                        for insumo_id in insumos_eliminados:
                            try:
                                ServicioInsumo.objects.filter(
                                    servicio=servicio,
                                    insumo_id=insumo_id
                                ).delete()
                            except Exception:
                                pass
                        
                        # VALIDAR QUE HAYA AL MENOS 1 INSUMO ACTIVO
                        insumos_activos = ServicioInsumo.objects.filter(servicio=servicio).count()
                        if insumos_activos == 0:
                            messages.error(request, "El servicio debe tener al menos un insumo")
                        
                        # Recalcular costo de insumos
                        try:
                            servicio.actualizar_costo_insumos()
                        except Exception as e:
                            print(f"Error calculando costo de insumos: {e}")
                        
                    messages.success(request, f"Servicio {servicio.nombre} actualizado")
                    return redirect("servicio_lista")
                    
                except ValidationError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f"Error al guardar el servicio: {str(e)}")
        else:
            form = ServicioEditarForm(instance=s)

        return render(request, "servicio/servicio_editar.html", {
            "form": form, 
            "servicio": s, 
            "puede_desactivar_servicios": puede_desactivar_servicios,
            "insumos_servicio": insumos_servicio,
            "insumos_disponibles": insumos_disponibles
        })
        
    except Servicio.DoesNotExist:
        messages.error(request, "El servicio no existe.")
        return redirect("servicio_lista")
    except Exception as e:
        messages.error(request, f"Error al cargar el servicio: {str(e)}")
        return redirect("servicio_lista")


@login_required
@permission_required('servicio.desactivar_servicios', raise_exception=True)
def servicio_desactivar(request, servicio_id):
    s = get_object_or_404(Servicio, pk=servicio_id)
    s.is_active = not s.is_active
    s.save(update_fields=["is_active"])
    estado = "activado" if s.is_active else "desactivado"
    messages.success(request, f"Servicio {s.nombre} {estado}")
    return redirect("servicio_lista")


@login_required
@permission_required('seguridad.ver_servicios', raise_exception=True)
def servicio_lista(request):
    q = (request.GET.get("q") or "").strip()
    cat = (request.GET.get("categoria") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    filtro_stock = (request.GET.get("stock") or "").strip()   

    qs = Servicio.objects.all()
    if q:
        qs = qs.filter(id__icontains=q) | qs.filter(nombre__icontains=q)
    if cat:
        qs = qs.filter(categoria__icontains=cat)
    if estado == "activo":
        qs = qs.filter(is_active=True)
    elif estado == "inactivo":
        qs = qs.filter(is_active=False)

    # Obtener todos los servicios (sin paginar aún)
    servicios_list = list(qs.order_by("nombre"))
    
    # Verificar stock para cada servicio y aplicar filtro si es necesario
    servicios_filtrados = []
    for servicio in servicios_list:
        # Verificar stock usando la misma función que en el template
        try:
            from .views import verificar_stock_servicio as verificar
            tiene_stock = verificar(servicio)  
        except:
            # Si no se puede importar, hacer una verificación simple
            tiene_stock = True
            for si in servicio.servicioinsumo_set.all():
                if si.cantidad > si.insumo.stock_actual:
                    tiene_stock = False
                    break
        
        # Aplicar filtro de stock
        if filtro_stock == "con_stock" and not tiene_stock:
            continue
        if filtro_stock == "sin_stock" and tiene_stock:
            continue
            
        # Agregar el servicio con su estado de stock
        servicio.tiene_stock = tiene_stock
        servicios_filtrados.append(servicio)

    # PAGINACIÓN sobre la lista filtrada
    from django.core.paginator import Paginator
    paginator = Paginator(servicios_filtrados, 10)
    page = request.GET.get("page")
    servicios = paginator.get_page(page)

    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()

    categorias_qs = (Servicio.objects
                    .exclude(categoria__isnull=True)
                    .exclude(categoria__exact='')
                    .values_list('categoria', flat=True)
                    .distinct()
                    .order_by('categoria'))
    categorias = [(c, c) for c in categorias_qs]

    return render(request, "servicio/servicio_lista.html", {
        "servicios": servicios,
        "qs_no_page": qs_no_page,
        "categorias": categorias,
        "filtro_stock_actual": filtro_stock,  
    })
