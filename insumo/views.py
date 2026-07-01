from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError as ModelValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db import models
from .forms import InsumoForm, InsumoEditarForm, AltaStockForm, BajaStockForm, CrearSubInsumosForm
from django.utils.translation import gettext_lazy as _
from .models import GrupoInsumo, Insumo, SubInsumo, MovimientoStock
from decimal import Decimal
from servicio.models import Servicio, ServicioInsumo

# =======
# INSUMOS
# =======

@login_required
@permission_required('seguridad.agregar_insumos', raise_exception=True)
def insumo_crear(request):
    if request.method == "POST":
        form = InsumoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    insumo = form.save()
                messages.success(request, f"Insumo {insumo.nombre} creado")
                return redirect("insumo_lista")

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
                form.add_error("nombre", "Ya existe un insumo con ese nombre")
    else:
        form = InsumoForm()

    return render(request, "insumo/insumo_crear.html", {"form": form})


@login_required
@permission_required('seguridad.ver_insumos', raise_exception=True)
def insumo_ver(request, insumo_id):
    insumo = get_object_or_404(Insumo, pk=insumo_id)
    subinsumos = insumo.subinsumos.filter(is_active=True).order_by('numero')
    
    return render(request, "insumo/insumo_ver.html", {
        'insumo': insumo,
        'subinsumos': subinsumos,
    })


@login_required
@permission_required('seguridad.editar_insumos', raise_exception=True)
def insumo_editar(request, insumo_id):
    insumo = get_object_or_404(Insumo, pk=insumo_id)
    puede_desactivar_insumos = request.user.has_perm('seguridad.desactivar_insumos')

    if request.method == "POST":
        form = InsumoEditarForm(request.POST, instance=insumo)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                messages.success(request, f"Insumo {insumo.nombre} actualizado")
                return redirect("insumo_lista")
            except ModelValidationError as e:
                # Distribuir errores de modelo en campos o no-campo
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
        # cae al render con errores
    else:
        form = InsumoEditarForm(instance=insumo)

    return render(
        request,
        "insumo/insumo_editar.html",
        {
            'form': form,
            'insumo': insumo,
            'puede_desactivar_insumos': puede_desactivar_insumos,
        },
    )


@login_required
@permission_required('seguridad.desactivar_insumos', raise_exception=True)
def insumo_desactivar(request, insumo_id):
    insumo = get_object_or_404(Insumo, pk=insumo_id)

    try:
        # Intentar cambiar el estado
        insumo.is_active = not insumo.is_active
        insumo.full_clean()  # Esto activará la validación
        insumo.save(update_fields=["is_active"])

        estado = "activado" if insumo.is_active else "desactivado"
        messages.success(request, f"Insumo {insumo.nombre} {estado}")

    except ValidationError as e:
        # Mostrar el error de validación al usuario
        if 'is_active' in e.message_dict:
            messages.error(request, e.message_dict['is_active'][0])
        else:
            messages.error(request, "Error al cambiar el estado del insumo")

    return redirect("insumo_lista")


@login_required
@permission_required('seguridad.ver_insumos', raise_exception=True)
def insumo_lista(request):
    q = (request.GET.get('q') or '').strip()
    categoria = (request.GET.get('categoria') or '').strip()
    unidad = (request.GET.get('unidad') or '').strip()
    estado = request.GET.get('estado')
    grupo = request.GET.get('grupo', '').strip()

    insumos = Insumo.objects.all()

    # BÚSQUEDA MEJORADA - SOPORTA CÓDIGOS COMO INS-0001, REP-0001, etc.
    if q:
        # Buscar por código completo (ej: INS-0001, rep-0001)
        if '-' in q:
            parts = q.split('-')
            if len(parts) >= 2:
                prefijo_busqueda = parts[0].upper()
                numero_busqueda = parts[1] if len(parts) > 1 else ''
                
                # Mapeo de prefijos a valores de grupo
                prefijo_a_grupo = {
                    'INS': 'insumo',
                    'REP': 'repuesto',
                    'HER': 'herramienta',
                    'LYM': 'limpieza_mantenimiento',
                    'INSV': 'insumo_venta',
                }
                
                # Si el prefijo es válido, buscar por grupo e ID
                if prefijo_busqueda in prefijo_a_grupo:
                    if numero_busqueda and numero_busqueda.isdigit():
                        # Buscar por ID exacto
                        try:
                            insumos = insumos.filter(
                                grupo=prefijo_a_grupo[prefijo_busqueda],
                                id=int(numero_busqueda)
                            )
                        except ValueError:
                            pass
                    else:
                        # Buscar solo por grupo
                        insumos = insumos.filter(grupo=prefijo_a_grupo[prefijo_busqueda])
                else:
                    # Si el prefijo no es válido, buscar normalmente
                    insumos = insumos.filter(
                        Q(nombre__icontains=q) |
                        Q(id__icontains=q) |
                        Q(categoria__icontains=q)
                    )
            else:
                # Búsqueda normal
                insumos = insumos.filter(
                    Q(nombre__icontains=q) |
                    Q(id__icontains=q) |
                    Q(categoria__icontains=q)
                )
        else:
            # Si no tiene guión, buscar normalmente
            # También intentar buscar por ID si es número
            try:
                insumo_id = int(q)
                insumos = insumos.filter(
                    Q(nombre__icontains=q) |
                    Q(id=insumo_id) |
                    Q(categoria__icontains=q)
                )
            except ValueError:
                insumos = insumos.filter(
                    Q(nombre__icontains=q) |
                    Q(categoria__icontains=q)
                )

    # Filtro por categoría
    if categoria:
        insumos = insumos.filter(categoria=categoria)
    
    # Filtro por unidad
    if unidad:
        insumos = insumos.filter(unidad=unidad)
    
    # Filtro por grupo
    if grupo:
        insumos = insumos.filter(grupo=grupo)

    # Filtro por estado
    if estado == 'activo':
        insumos = insumos.filter(is_active=True)
    elif estado == 'inactivo':
        insumos = insumos.filter(is_active=False)

    insumos = insumos.order_by("nombre")

    paginator = Paginator(insumos, 10)
    page_number = request.GET.get('page')
    insumos = paginator.get_page(page_number)

    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()

    try:
        unidad_choices = Insumo._meta.get_field('unidad').choices
    except Exception:
        unidad_choices = []

    # Categorías existentes
    categorias_qs = (Insumo.objects
                    .exclude(categoria__isnull=True)
                    .exclude(categoria__exact='')
                    .values_list('categoria', flat=True)
                    .distinct()
                    .order_by('categoria'))
    categorias = [(c, c) for c in categorias_qs]

    # Grupos para el filtro
    grupos = GrupoInsumo.choices

    return render(
        request,
        "insumo/insumo_lista.html",
        {
            'insumos': insumos,
            'qs_no_page': qs_no_page,
            'categorias': categorias,
            'unidades': unidad_choices,
            'grupos': grupos, 
        }
    )


# ===========
# SUB-INSUMOS
# ===========

@login_required
@permission_required('seguridad.agregar_insumos', raise_exception=True)
def insumo_crear_subinsumos(request, insumo_id):
    """Vista para crear subinsumos de un insumo existente"""
    insumo = get_object_or_404(Insumo, pk=insumo_id)
    
    stock_libre = insumo.stock_disponible_para_subinsumos
    stock_fisico = insumo.stock_actual
    stock_en_subinsumos = stock_fisico - stock_libre
    
    if request.method == 'POST':
        form = CrearSubInsumosForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            cantidad_por_subinsumo = form.cleaned_data['cantidad_por_subinsumo']
            
            try:
                # Verificar si se pueden crear
                puede_crear, mensaje = insumo.puede_crear_subinsumos(cantidad, cantidad_por_subinsumo)
                
                if not puede_crear:
                    messages.error(request, mensaje)
                else:
                    # Crear los subinsumos
                    subinsumos_creados = insumo.crear_subinsumos(cantidad, cantidad_por_subinsumo)
                    messages.success(
                        request, 
                        _('Se crearon %(cantidad)s sub-insumos de %(tamano)s %(unidad)s cada uno para %(insumo)s') % {
                            'cantidad': cantidad,
                            'tamano': cantidad_por_subinsumo,
                            'unidad': insumo.unidad,
                            'insumo': insumo.nombre
                        }
                    )
                    return redirect('insumo_lista')
                    
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error al crear subinsumos: {str(e)}")
    else:
        form = CrearSubInsumosForm(initial={
            'cantidad': 1,
            'cantidad_por_subinsumo': 1
        })
    
    return render(request, 'insumo/subinsumo_crear.html', {
        'insumo': insumo,
        'form': form,
        'stock_libre': stock_libre,
        'stock_fisico': stock_fisico,
        'stock_en_subinsumos': stock_en_subinsumos,
    })


@login_required
@permission_required('seguridad.ver_insumos', raise_exception=True)
def subinsumo_lista(request):
    """Vista para listar todos los subinsumos con búsqueda por código"""
    q = (request.GET.get('q') or '').strip()
    insumo_padre_id = request.GET.get('insumo_padre')
    estado = request.GET.get('estado')
    stock = request.GET.get('stock')

    subinsumos = SubInsumo.objects.all().select_related('insumo_padre')

    # BÚSQUEDA MEJORADA - SOPORTA CÓDIGOS COMO INS-0001-0001, REP-0001-0001, etc.
    if q:
        q_upper = q.upper()
        
        # Buscar por código completo (formato: PREFIJO-ID-NUMERO)
        if '-' in q_upper:
            parts = q_upper.split('-')
            
            # Código de subinsumo: INS-0001-0001 (3 partes)
            if len(parts) == 3:
                prefijo_busqueda = parts[0]
                id_padre_busqueda = parts[1]
                numero_busqueda = parts[2]
                
                prefijo_a_grupo = {
                    'INS': 'insumo',
                    'REP': 'repuesto',
                    'HER': 'herramienta',
                    'LYM': 'limpieza_mantenimiento',
                    'INSV': 'insumo_venta',
                }
                
                if prefijo_busqueda in prefijo_a_grupo and id_padre_busqueda.isdigit():
                    try:
                        # Buscar por el código generado en la base de datos
                        subinsumos = subinsumos.filter(
                            codigo_generado__icontains=q_upper
                        )
                        
                        # Si no encuentra por código generado, buscar por padre y número
                        if not subinsumos.exists():
                            subinsumos = subinsumos.filter(
                                insumo_padre__grupo=prefijo_a_grupo[prefijo_busqueda],
                                insumo_padre__id=int(id_padre_busqueda),
                                numero=int(numero_busqueda) if numero_busqueda.isdigit() else 0
                            )
                    except ValueError:
                        subinsumos = subinsumos.filter(
                            Q(codigo_generado__icontains=q_upper) |
                            Q(nombre__icontains=q) |
                            Q(insumo_padre__nombre__icontains=q)
                        )
                else:
                    subinsumos = subinsumos.filter(
                        Q(codigo_generado__icontains=q_upper) |
                        Q(nombre__icontains=q) |
                        Q(insumo_padre__nombre__icontains=q)
                    )
            
            # Código de insumo padre: INS-0001 (2 partes)
            elif len(parts) == 2:
                prefijo_busqueda = parts[0]
                id_padre_busqueda = parts[1]
                
                prefijo_a_grupo = {
                    'INS': 'insumo',
                    'REP': 'repuesto',
                    'HER': 'herramienta',
                    'LYM': 'limpieza_mantenimiento',
                    'INSV': 'insumo_venta',
                }
                
                if prefijo_busqueda in prefijo_a_grupo and id_padre_busqueda.isdigit():
                    try:
                        subinsumos = subinsumos.filter(
                            insumo_padre__grupo=prefijo_a_grupo[prefijo_busqueda],
                            insumo_padre__id=int(id_padre_busqueda)
                        )
                    except ValueError:
                        subinsumos = subinsumos.filter(
                            Q(codigo_generado__icontains=q_upper) |
                            Q(nombre__icontains=q) |
                            Q(insumo_padre__nombre__icontains=q)
                        )
                else:
                    subinsumos = subinsumos.filter(
                        Q(codigo_generado__icontains=q_upper) |
                        Q(nombre__icontains=q) |
                        Q(insumo_padre__nombre__icontains=q)
                    )
            else:
                subinsumos = subinsumos.filter(
                    Q(codigo_generado__icontains=q_upper) |
                    Q(nombre__icontains=q) |
                    Q(insumo_padre__nombre__icontains=q)
                )
        else:
            # Búsqueda normal (sin guión)
            # Buscar por ID del insumo padre si es número
            try:
                padre_id = int(q)
                subinsumos = subinsumos.filter(
                    Q(nombre__icontains=q) |
                    Q(insumo_padre__nombre__icontains=q) |
                    Q(insumo_padre_id=padre_id) |
                    Q(codigo_generado__icontains=q_upper)
                )
            except ValueError:
                subinsumos = subinsumos.filter(
                    Q(nombre__icontains=q) |
                    Q(insumo_padre__nombre__icontains=q) |
                    Q(codigo_generado__icontains=q_upper)
                )

    if insumo_padre_id and insumo_padre_id != '':
        subinsumos = subinsumos.filter(insumo_padre_id=insumo_padre_id)

    if estado == 'activo':
        subinsumos = subinsumos.filter(is_active=True)
    elif estado == 'inactivo':
        subinsumos = subinsumos.filter(is_active=False)

    if stock == 'agotado':
        subinsumos = subinsumos.filter(stock_actual=0)

    subinsumos = subinsumos.order_by('-fecha_creacion')

    # Estadísticas
    total_subinsumos = subinsumos.count()
    subinsumos_activos = SubInsumo.objects.filter(is_active=True).count()
    subinsumos_inactivos = SubInsumo.objects.filter(is_active=False).count()
    subinsumos_agotados = SubInsumo.objects.filter(stock_actual=0, is_active=True).count()
    stock_total = SubInsumo.objects.aggregate(total=models.Sum('stock_actual'))['total'] or 0

    insumos_padre = Insumo.objects.filter(is_active=True).order_by('nombre')

    paginator = Paginator(subinsumos, 15)
    page_number = request.GET.get('page')
    subinsumos_paginados = paginator.get_page(page_number)

    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()

    context = {
        'subinsumos': subinsumos_paginados,
        'insumos_padre': insumos_padre,
        'total_subinsumos': total_subinsumos,
        'subinsumos_activos': subinsumos_activos,
        'subinsumos_inactivos': subinsumos_inactivos,
        'subinsumos_agotados': subinsumos_agotados,
        'stock_total': stock_total,
        'qs_no_page': qs_no_page,
    }
    return render(request, 'insumo/subinsumo_lista.html', context)


# =====
# STOCK
# =====

@login_required
@permission_required('seguridad.ver_insumos', raise_exception=True)
def stock_control(request):
    """Vista principal del control de stock"""
    # Obtener el filtro del parámetro GET
    q = (request.GET.get('q') or '').strip()
    filtro = request.GET.get('filtro', 'todos')
    
    # Base queryset
    insumos = Insumo.objects.filter(is_active=True).order_by('nombre')
    
    if q:
        insumos = insumos.filter(
            Q(nombre__icontains=q) |
            Q(id__icontains=q) |
            Q(categoria__icontains=q)
        )
        
    # Aplicar filtros según el parámetro
    if filtro == 'normal':
        insumos = insumos.filter(stock_actual__gt=models.F('stock_minimo'))
    if filtro == 'bajos':
        insumos = insumos.filter(stock_actual__lte=models.F('stock_minimo')).exclude(stock_actual=0)
    elif filtro == 'agotados':
        insumos = insumos.filter(stock_actual=0)
    
    # Estadísticas (siempre calculadas sobre todos los insumos activos)
    todos_insumos = Insumo.objects.filter(is_active=True)
    total_insumos = todos_insumos.count()
    insumos_normal = todos_insumos.filter(stock_actual__gt=models.F('stock_minimo'))
    insumos_bajos = todos_insumos.filter(stock_actual__lte=models.F('stock_minimo')).exclude(stock_actual=0)
    insumos_agotados = todos_insumos.filter(stock_actual=0)
    
    # PAGINACIÓN - 10 items por página
    paginator = Paginator(insumos, 10)
    page_number = request.GET.get('page')
    insumos_paginados = paginator.get_page(page_number)
    
    # Mantener parámetros GET para paginación
    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()
    
    context = {
        'insumos': insumos_paginados,  
        'total_insumos': total_insumos,
        'insumos_normal': insumos_normal,
        'insumos_bajos': insumos_bajos,
        'insumos_agotados': insumos_agotados,
        'filtro_actual': filtro,
        'qs_no_page': qs_no_page,  
    }
    return render(request, 'insumo/stock_control.html', context)


@login_required
@permission_required('seguridad.gestionar_stock_insumos', raise_exception=True)
def stock_alta(request):
    """Vista para dar de alta stock"""
    if request.method == 'POST':
        form = AltaStockForm(request.POST)
        if form.is_valid():
            insumo = form.cleaned_data['insumo']
            cantidad = form.cleaned_data['cantidad']
            motivo = form.cleaned_data['motivo']
            observaciones = form.cleaned_data['observaciones']
            
            # Crear movimiento de entrada
            movimiento = MovimientoStock(
                insumo=insumo,
                tipo='entrada',
                cantidad=cantidad,
                motivo=motivo,
                observaciones=observaciones,
                usuario=request.user
            )
            movimiento.save()
            
            messages.success(
                request, 
                _('Se agregaron %(cantidad)s %(unidad)s de %(insumo)s al stock') % {
                    'cantidad': cantidad,
                    'unidad': insumo.unidad,
                    'insumo': insumo.nombre
                }
            )
            return redirect('stock_control')
    else:
        form = AltaStockForm()
    
    context = {'form': form, 'titulo': _('AGREGAR STOCK')}
    return render(request, 'insumo/stock_movimiento.html', context)


@login_required
@permission_required('seguridad.gestionar_stock_insumos', raise_exception=True)
def stock_baja(request):
    """Vista para dar de baja stock - maneja subinsumos automáticamente"""
    if request.method == 'POST':
        form = BajaStockForm(request.POST)
        if form.is_valid():
            insumo = form.cleaned_data['insumo']
            cantidad = form.cleaned_data['cantidad']  # Esto ya es Decimal
            motivo = form.cleaned_data['motivo']
            observaciones = form.cleaned_data['observaciones']
            
            # VERIFICAR STOCK FÍSICO TOTAL
            stock_fisico = insumo.stock_fisico_real
            
            if cantidad > stock_fisico:
                messages.error(
                    request, 
                    _("No hay suficiente stock disponible. Stock físico total: %(stock)s %(unidad)s") % {
                        'stock': stock_fisico,
                        'unidad': insumo.unidad
                    }
                )
                return redirect('stock_baja')
            
            # VERIFICAR SI HAY SUBINSUMOS DISPONIBLES
            subinsumos_disponibles = insumo.subinsumos.filter(is_active=True, stock_actual__gt=0)
            total_en_subinsumos = subinsumos_disponibles.aggregate(
                total=models.Sum('stock_actual')
            )['total'] or Decimal('0')
            
            # CALCULAR STOCK LIBRE
            stock_libre = insumo.stock_disponible_para_subinsumos
            
            # VERIFICAR SI LA CANTIDAD ES VÁLIDA PARA ALGUNA OPCIÓN
            cantidad_valida_subinsumos = cantidad <= total_en_subinsumos
            cantidad_valida_stock_libre = cantidad <= stock_libre
            
            # CAMBIO IMPORTANTE: Si hay subinsumos activos, SIEMPRE redirigir a confirmación
            # PERO solo mostrar mensaje informativo si la cantidad es válida para al menos una opción
            if subinsumos_disponibles.exists():
                # Guardar en sesión para redirección a confirmación
                request.session['baja_pendiente'] = {
                    'insumo_id': insumo.id,
                    'cantidad': float(cantidad),
                    'motivo': motivo,
                    'observaciones': observaciones
                }
                
                # SOLO mostrar mensaje informativo si la cantidad es válida para al menos una opción
                if cantidad_valida_subinsumos or cantidad_valida_stock_libre:
                    messages.info(
                        request,
                        _("Existen sub-insumos activos. Seleccione cómo desea realizar el retiro.")
                    )
                # Si no es válida para ninguna, no mostrar mensaje (el error se mostrará en la confirmación)
                
                return redirect('stock_baja_confirmar_subinsumos')
            
            # SOLO si NO hay subinsumos activos, proceder directamente
            movimiento = MovimientoStock(
                insumo=insumo,
                tipo='salida',
                cantidad=cantidad,
                motivo=motivo,
                observaciones=observaciones,
                usuario=request.user
            )
            movimiento.save()
            
            messages.success(
                request, 
                _('Se retiraron %(cantidad)s %(unidad)s de %(insumo)s del stock') % {
                    'cantidad': cantidad,
                    'unidad': insumo.unidad,
                    'insumo': insumo.nombre
                }
            )
            return redirect('stock_control')
    else:
        form = BajaStockForm()
    
    context = {'form': form, 'titulo': _('RETIRAR STOCK')}
    return render(request, 'insumo/stock_movimiento.html', context)


@login_required
@permission_required('seguridad.gestionar_stock_insumos', raise_exception=True)
def stock_baja_confirmar_subinsumos(request):
    """Vista para confirmar consumo de subinsumos específicos"""
    # Obtener datos de la sesión
    baja_pendiente = request.session.get('baja_pendiente')
    if not baja_pendiente:
        messages.error(request, _("No hay una baja de stock pendiente"))
        return redirect('stock_baja')
    
    insumo_principal = get_object_or_404(Insumo, pk=baja_pendiente['insumo_id'])
    cantidad_decimal = Decimal(str(baja_pendiente['cantidad']))
    
    # CALCULAR STOCK LIBRE Y TOTAL EN SUBINSUMOS
    stock_libre = insumo_principal.stock_disponible_para_subinsumos
    subinsumos_disponibles = insumo_principal.subinsumos.filter(is_active=True, stock_actual__gt=0)
    total_en_subinsumos = subinsumos_disponibles.aggregate(
        total=models.Sum('stock_actual')
    )['total'] or Decimal('0')
    
    # Verificar si la cantidad NO es válida para ninguna opción
    cantidad_valida_subinsumos = cantidad_decimal <= total_en_subinsumos
    cantidad_valida_stock_libre = cantidad_decimal <= stock_libre
    
    # Si no es válida para ninguna opción, mostrar error específico
    if not cantidad_valida_subinsumos and not cantidad_valida_stock_libre:
        messages.error(
            request,
            _("La cantidad solicitada (%(cantidad)s %(unidad)s) no es válida para ninguna opción. Stock libre: %(stock_libre)s %(unidad)s, Stock en sub-insumos: %(subinsumos)s %(unidad)s") % {
                'cantidad': cantidad_decimal,
                'stock_libre': stock_libre,
                'subinsumos': total_en_subinsumos,
                'unidad': insumo_principal.unidad
            }
        )
        # Limpiar sesión y redirigir a stock_baja para que corrija la cantidad
        del request.session['baja_pendiente']
        return redirect('stock_baja')
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'consumir_subinsumos':
            # Solo permitir si la cantidad es válida para subinsumos
            if cantidad_valida_subinsumos:
                return redirect('stock_baja_seleccionar_subinsumos')
            else:
                messages.error(
                    request,
                    _("No puede consumir sub-insumos porque la cantidad (%(cantidad)s) es mayor al total disponible en sub-insumos (%(subinsumos)s)") % {
                        'cantidad': cantidad_decimal,
                        'subinsumos': total_en_subinsumos
                    }
                )
                
        elif accion == 'continuar_normal':
            # Solo permitir si la cantidad es válida para stock libre
            if cantidad_valida_stock_libre:
                movimiento = MovimientoStock(
                    insumo=insumo_principal,
                    tipo='salida',
                    cantidad=cantidad_decimal,
                    motivo=baja_pendiente['motivo'],
                    observaciones=baja_pendiente['observaciones'],
                    usuario=request.user
                )
                movimiento.save()
                
                # Limpiar sesión
                del request.session['baja_pendiente']
                
                messages.success(
                    request, 
                    _('Se retiraron %(cantidad)s %(unidad)s de %(insumo)s del stock') % {
                        'cantidad': baja_pendiente['cantidad'],
                        'unidad': insumo_principal.unidad,
                        'insumo': insumo_principal.nombre
                    }
                )
                return redirect('stock_control')
            else:
                messages.error(
                    request,
                    _("No hay suficiente stock libre disponible. Stock libre: %(stock_libre)s %(unidad)s") % {
                        'stock_libre': stock_libre,
                        'unidad': insumo_principal.unidad
                    }
                )
        else:
            # Cancelar
            del request.session['baja_pendiente']
            return redirect('stock_baja')
    
    # Obtener información de subinsumos para mostrar
    subinsumos = subinsumos_disponibles
    
    return render(request, 'insumo/stock_baja_confirmar.html', {
        'insumo_principal': insumo_principal,
        'cantidad': baja_pendiente['cantidad'],
        'motivo': baja_pendiente['motivo'],
        'subinsumos': subinsumos,
        'total_subinsumos': total_en_subinsumos,
        'stock_libre': stock_libre,
        'hay_stock_libre': cantidad_valida_stock_libre,
        'puede_consumir_subinsumos': cantidad_valida_subinsumos
    })


@login_required
@permission_required('seguridad.gestionar_stock_insumos', raise_exception=True)
def stock_baja_seleccionar_subinsumos(request):
    """Vista para seleccionar subinsumos específicos a consumir"""
    baja_pendiente = request.session.get('baja_pendiente')
    if not baja_pendiente:
        messages.error(request, _("No hay una baja de stock pendiente"))
        return redirect('stock_baja')
    
    insumo_principal = get_object_or_404(Insumo, pk=baja_pendiente['insumo_id'])
    cantidad_necesaria = Decimal(str(baja_pendiente['cantidad']))
    
    if request.method == 'POST':
        subinsumos_seleccionados = request.POST.getlist('subinsumos')
        
        if not subinsumos_seleccionados:
            messages.error(request, _("Debe seleccionar al menos un sub-insumo"))
        else:
            total_seleccionado = 0
            subinsumos_a_consumir = []
            
            # Calcular total seleccionado
            for sub_id in subinsumos_seleccionados:
                subinsumo = get_object_or_404(SubInsumo, pk=sub_id)
                total_seleccionado += subinsumo.stock_actual
                subinsumos_a_consumir.append(subinsumo)
            
            if total_seleccionado != cantidad_necesaria:
                messages.error(
                    request,
                    _("La suma de los sub-insumos seleccionados (%(seleccionado)s) no coincide con la cantidad necesaria (%(necesaria)s)") % {
                        'seleccionado': total_seleccionado,
                        'necesaria': cantidad_necesaria
                    }
                )
            else:
                # Consumir los subinsumos
                with transaction.atomic():
                    for subinsumo in subinsumos_a_consumir:
                        # Desactivar el subinsumo
                        subinsumo.is_active = False
                        subinsumo.stock_actual = 0
                        subinsumo.save()
                    
                    # Crear movimiento de stock
                    movimiento = MovimientoStock(
                        insumo=insumo_principal,
                        tipo='salida',
                        cantidad=cantidad_necesaria,
                        motivo=baja_pendiente['motivo'],
                        observaciones=f"{baja_pendiente['observaciones']} - Consumidos {len(subinsumos_a_consumir)} sub-insumos",
                        usuario=request.user
                    )
                    movimiento.save()
                
                # Limpiar sesión
                del request.session['baja_pendiente']
                
                messages.success(
                    request,
                    _('Se consumieron %(cantidad)s %(unidad)s mediante %(count)s sub-insumos') % {
                        'cantidad': cantidad_necesaria,
                        'unidad': insumo_principal.unidad,
                        'count': len(subinsumos_a_consumir)
                    }
                )
                return redirect('stock_control')
    
    # Obtener subinsumos disponibles
    subinsumos_disponibles = insumo_principal.subinsumos.filter(is_active=True, stock_actual__gt=0)
    
    return render(request, 'insumo/stock_baja_seleccionar.html', {
        'insumo_principal': insumo_principal,
        'cantidad_necesaria': cantidad_necesaria,
        'subinsumos': subinsumos_disponibles,
        'total_disponible': subinsumos_disponibles.aggregate(total=models.Sum('stock_actual'))['total'] or 0
    })


@login_required
@permission_required('seguridad.ver_insumos', raise_exception=True)
def stock_historial(request, insumo_id=None):
    """Vista para ver el historial de movimientos"""
    # Obtener el filtro del parámetro GET
    filtro = request.GET.get('filtro', 'todos')
    
    # Base queryset
    if insumo_id:
        insumo = get_object_or_404(Insumo, id=insumo_id)
        movimientos = MovimientoStock.objects.filter(insumo=insumo)
    else:
        insumo = None
        movimientos = MovimientoStock.objects.all()
    
    # Aplicar filtros según el parámetro
    if filtro == 'entradas':
        movimientos = movimientos.filter(tipo='entrada')
    elif filtro == 'salidas':
        movimientos = movimientos.filter(tipo='salida')
    # 'todos' e 'insumos' no aplican filtro adicional
    
    # Ordenar por fecha más reciente primero
    movimientos = movimientos.order_by('-fecha_movimiento')
    
    # Estadísticas (siempre calculadas sobre todos los movimientos)
    todos_movimientos = MovimientoStock.objects.all()
    total_movimientos = todos_movimientos.count()
    total_entradas = todos_movimientos.filter(tipo='entrada').count()
    total_salidas = todos_movimientos.filter(tipo='salida').count()
    total_insumos = Insumo.objects.filter(is_active=True).count()
    
    # PAGINACIÓN - 10 items por página
    paginator = Paginator(movimientos, 10)
    page_number = request.GET.get('page')
    movimientos_paginados = paginator.get_page(page_number)
    
    # Mantener parámetros GET para paginación
    qs = request.GET.copy()
    qs.pop('page', None)
    qs_no_page = qs.urlencode()
    
    context = {
        'movimientos': movimientos_paginados,
        'insumo': insumo,
        'total_movimientos': total_movimientos,
        'total_entradas': total_entradas,
        'total_salidas': total_salidas,
        'total_insumos': total_insumos,
        'filtro_actual': filtro,
        'qs_no_page': qs_no_page,
    }
    return render(request, 'insumo/stock_historial.html', context)


@login_required
def buscar_insumos_movimiento(request):
    """Vista para autocompletar insumos para movimientos de stock"""
    query = request.GET.get('q', '').strip()
    
    try:
        # SOLO insumos activos
        insumos = Insumo.objects.filter(is_active=True)
        
        # Aplicar filtro de búsqueda si hay query
        if query:
            insumos = insumos.filter(
                Q(nombre__icontains=query) |
                Q(id__icontains=query) |
                Q(categoria__icontains=query) 
            )
        
        # Ordenar y limitar resultados
        insumos = insumos.order_by('nombre')[:10]
        
        # Formatear respuesta
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.pk,
                'text': f"{insumo.nombre}",
                'nombre': insumo.nombre,
                'categoria': insumo.categoria if insumo.categoria else 'Sin categoría',
                'stock_actual': str(insumo.stock_actual),
                'unidad': insumo.unidad if insumo.unidad else 'Sin unidad',
            })
        
        return JsonResponse(insumos_data, safe=False)
        
    except Exception as e:
        print(f"Error en buscar_insumos_movimiento: {e}")
        return JsonResponse([], safe=False)


@login_required
def verificar_stock_servicio(request, servicio_id):
    cantidad = request.GET.get('cantidad', 1)
    
    try:
        cantidad = Decimal(str(cantidad))
        servicio = Servicio.objects.get(id=servicio_id, is_active=True)
        
        insumos_faltantes = []
        
        for si in servicio.servicioinsumo_set.all():
            insumo = si.insumo
            cantidad_necesaria = si.cantidad * cantidad
            
            if cantidad_necesaria > insumo.stock_actual:
                insumos_faltantes.append({
                    'nombre': insumo.nombre,
                    'necesario': float(cantidad_necesaria),
                    'disponible': float(insumo.stock_actual),
                    'faltante': float(cantidad_necesaria - insumo.stock_actual),
                    'unidad': insumo.get_unidad_display()
                })
        
        return JsonResponse({'insumos_faltantes': insumos_faltantes})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)