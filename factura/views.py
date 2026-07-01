# pylint: disable=no-member, line-too-long, missing-module-docstring, missing-function-docstring
# pylint: disable=unused-argument
# pylint: disable=unused-import
# pylint: disable=broad-exception-caught

# STANDARD
from decimal import Decimal
import os
import json
from datetime import timedelta
from xml.dom import ValidationErr

# DJANGO
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings

#  APPS
from cliente.models import Cliente
from seguridad.models import ConfiguracionSistema
from insumo.models import Insumo
from servicio.models import Servicio

# LOCALES
from .models import Factura, FacturaSerie, FacturaServicio, FacturaInsumo, NotaCredito, NotaCreditoDetalle
from .forms import FacturaEmitirForm, ItemFacturaFormSet, ServicioFormSet, InsumoFormSet
from finanza.views import crear_movimiento_factura, crear_movimiento_nota_credito, anular_movimiento_factura


@login_required
@permission_required('seguridad.ver_facturas', raise_exception=True)
def factura_inicio(request):
    hoy = timezone.localdate()
    ctx = {
        "total_hoy": Factura.objects.filter(fecha=hoy).count(),
        "anuladas_hoy": Factura.objects.filter(fecha=hoy, estado=Factura.Estado.ANULADA).count(),
        "activas": Factura.objects.filter(estado=Factura.Estado.ACTIVA).count(),
        "anuladas": Factura.objects.filter(estado=Factura.Estado.ANULADA).count(),
    }
    return render(request, "factura/factura_inicio.html", ctx)


def obtener_insumo_desde_descripcion(descripcion):
    """
    Obtiene un insumo a partir de la descripción.
    Busca por: código completo (INSV-XXXX) o por nombre.
    """
    import re
    print(f"DEBUG obtener_insumo: descripcion='{descripcion}'")
    
    # Buscar por código INSV-XXXX o REP-XXXX o INS-XXXX
    codigo_match = re.search(r'(INSV|REP|INS|HER|LYM)-(\d+)', descripcion)
    if codigo_match:
        numero = int(codigo_match.group(2))
        try:
            insumo = Insumo.objects.get(id=numero, grupo='insumo_venta', is_active=True)
            print(f"DEBUG: Insumo encontrado por código: {insumo.nombre} (stock: {insumo.stock_actual})")
            return insumo
        except Insumo.DoesNotExist:
            print(f"DEBUG: No se encontró insumo con ID {numero}")
    
    # Buscar por ID en formato [ID]
    id_match = re.search(r'\[(\d+)\]', descripcion)
    if id_match:
        insumo_id = int(id_match.group(1))
        try:
            insumo = Insumo.objects.get(id=insumo_id, grupo='insumo_venta', is_active=True)
            print(f"DEBUG: Insumo encontrado por ID: {insumo.nombre} (stock: {insumo.stock_actual})")
            return insumo
        except Insumo.DoesNotExist:
            print(f"DEBUG: No se encontró insumo con ID {insumo_id}")
    
    # Buscar por nombre (exacto o parcial)
    try:
        insumo = Insumo.objects.get(nombre__iexact=descripcion, grupo='insumo_venta', is_active=True)
        print(f"DEBUG: Insumo encontrado por nombre exacto: {insumo.nombre} (stock: {insumo.stock_actual})")
        return insumo
    except Insumo.DoesNotExist:
        pass
    except Insumo.MultipleObjectsReturned:
        insumo = Insumo.objects.filter(nombre__iexact=descripcion, grupo='insumo_venta', is_active=True).first()
        if insumo:
            print(f"DEBUG: Insumo encontrado por nombre exacto (primero): {insumo.nombre} (stock: {insumo.stock_actual})")
            return insumo
    
    # Buscar por nombre parcial
    try:
        insumos = Insumo.objects.filter(nombre__icontains=descripcion, grupo='insumo_venta', is_active=True)
        if insumos.exists():
            insumo = insumos.first()
            print(f"DEBUG: Insumo encontrado por nombre parcial: {insumo.nombre} (stock: {insumo.stock_actual})")
            return insumo
    except Exception as e:
        print(f"DEBUG: Error buscando por nombre parcial: {e}")
    
    print("DEBUG: No se encontró ningún insumo")
    return None


def validar_stock_insumo(descripcion, cantidad):
    """Valida si un insumo tiene stock suficiente"""
    insumo = obtener_insumo_desde_descripcion(descripcion)
    
    if insumo:
        if cantidad > insumo.stock_actual:
            return False, insumo, cantidad
        return True, insumo, cantidad
    
    return True, None, 0


def descontar_stock_insumo(descripcion, cantidad):
    """Descuenta stock de un insumo"""
    insumo = obtener_insumo_desde_descripcion(descripcion)
    
    if insumo:
        insumo.stock_actual -= Decimal(str(cantidad))
        insumo.save(update_fields=['stock_actual'])
        print(f"DEBUG: Stock DESCONTADO de {insumo.nombre}: {cantidad} {insumo.unidad} (nuevo stock: {insumo.stock_actual})")
        return True
    
    print(f"DEBUG: No se encontró insumo para descontar: {descripcion}")
    return False


def reponer_stock_insumo(descripcion, cantidad):
    """Repone stock de un insumo"""
    insumo = obtener_insumo_desde_descripcion(descripcion)
    
    if insumo:
        insumo.stock_actual += Decimal(str(cantidad))
        insumo.save(update_fields=['stock_actual'])
        print(f"DEBUG: Stock REPUESTO de {insumo.nombre}: {cantidad} {insumo.unidad} (nuevo stock: {insumo.stock_actual})")
        return True
    
    print(f"DEBUG: No se encontró insumo para reponer: {descripcion}")
    return False


@login_required
@permission_required('seguridad.agregar_facturas', raise_exception=True)
@transaction.atomic
def factura_emitir(request):
    from decimal import Decimal
    
    # ========== OBTENER ORDEN_ID SI VIENE DESDE OT ==========
    orden_id = request.GET.get('orden_id')
    orden = None
    servicios_precargados = []
    cliente_precargado = None
    
    if orden_id:
        try:
            from orden_trabajo.models import OrdenTrabajo
            orden = OrdenTrabajo.objects.get(id=orden_id, estado='aprobado')
            cliente_precargado = orden.cliente
            
            for servicio_orden in orden.ordenservicio_set.select_related('servicio').all():
                servicios_precargados.append({
                    'id': servicio_orden.servicio.id,
                    'nombre': servicio_orden.servicio.nombre,
                    'cantidad': float(servicio_orden.cantidad),
                    'precio': float(servicio_orden.precio_unitario),
                    'subtotal': float(servicio_orden.subtotal),
                })
            
            messages.info(request, f"Factura precargada desde OT #{orden.id}")
            
        except OrdenTrabajo.DoesNotExist:
            messages.warning(request, "Orden no encontrada o no está aprobada")
    
    # ========== CONFIGURACIÓN ==========
    def get_config(clave, default=""):
        try:
            return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
        except ConfiguracionSistema.DoesNotExist:
            return default

    timbrado_actual = get_config("timbrado_numero")
    valido_hasta = get_config("timbrado_vencimiento")
    establecimiento = get_config("establecimiento", "001")
    punto_emision = get_config("punto_emision", "001")

    if not timbrado_actual:
        messages.error(request, "No hay timbrado configurado")

    try:
        proximo_numero = FacturaSerie.siguiente(establecimiento, punto_emision, timbrado_actual)
        numero_formateado = f"{establecimiento}-{punto_emision}-{proximo_numero:07d}"
    except (ValueError, TypeError):
        proximo_numero = 1
        numero_formateado = f"{establecimiento}-{punto_emision}-0000001"

    initial_data = {
        'fecha': timezone.localdate(),
        'numero_factura': numero_formateado,
        'timbrado': timbrado_actual,
        'valido_hasta': valido_hasta,
    }

    if request.method == "POST":
        form = FacturaEmitirForm(request.POST)
        post_data = request.POST.copy()
        post_data["fecha"] = post_data.get("fecha_emision")
        form = FacturaEmitirForm(post_data)
        
        item_formset = ItemFacturaFormSet(request.POST, prefix="items")
        
        # ========== VALIDAR STOCK DE INSUMOS ANTES DE CREAR FACTURA ==========
        errores_stock = []
        items_validados = []

        if item_formset.is_valid():
            for item_form in item_formset:
                if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                    continue
                
                tipo = item_form.cleaned_data.get("tipo", "insumo")
                if not tipo:
                    tipo = "insumo"
                
                descripcion = item_form.cleaned_data.get("descripcion")
                cantidad = item_form.cleaned_data.get("cantidad") or 0
                precio = item_form.cleaned_data.get("precio_unitario") or 0
                
                print(f"DEBUG item: tipo={tipo}, descripcion={descripcion}, cantidad={cantidad}, precio={precio}")
                
                if tipo == "insumo":
                    ok, insumo, cant = validar_stock_insumo(descripcion, cantidad)
                    if not ok:
                        errores_stock.append(
                            f"{insumo.nombre}: necesita {cant} {insumo.unidad}, "
                            f"stock disponible: {insumo.stock_actual} {insumo.unidad}"
                        )
                    else:
                        items_validados.append({
                            'tipo': tipo,
                            'descripcion': descripcion,
                            'cantidad': cantidad,
                            'precio': precio,
                            'insumo': insumo,
                        })
                else:
                    items_validados.append({
                        'tipo': tipo,
                        'descripcion': descripcion,
                        'cantidad': cantidad,
                        'precio': precio,
                        'insumo': None,
                    })
        
        if errores_stock:
            for error in errores_stock:
                messages.error(request, f"Stock insuficiente: {error}")
            return redirect("factura_emitir")
        
        if form.is_valid() and item_formset.is_valid():
            try:
                factura = form.save(commit=False)
                factura.establecimiento = establecimiento
                factura.punto_emision = punto_emision
                factura.timbrado = timbrado_actual
                factura.configuracion_impresion = None
                factura.sin_ot = not bool(orden_id)
               
                if orden_id and orden:
                    factura.numero_ot = orden_id
                    factura.cliente = orden.cliente
                    factura.cliente_nombre = orden.cliente.nombre
                    factura.cliente_ruc = orden.cliente.numero_documento
                    factura.cliente_direccion = orden.cliente.direccion
                    factura.cliente_telefono = orden.cliente.telefono
                else:
                    cliente_id = request.POST.get("cliente")
                    if cliente_id:
                        try:
                            factura.cliente = Cliente.objects.get(id=cliente_id)
                        except Cliente.DoesNotExist:
                            factura.cliente = None

                factura.save()

                total_items = 0

                # ========== PROCESAR SERVICIOS PRECARGADOS (DESDE OT) ==========
                if orden_id and orden:
                    for servicio_data in servicios_precargados:
                        FacturaServicio.objects.create(
                            factura=factura,
                            descripcion=servicio_data['nombre'],
                            cantidad=servicio_data['cantidad'],
                            precio_unitario=servicio_data['precio'],
                        )
                        total_items += 1

                # ========== PROCESAR ITEMS DEL FORMSET Y DESCONTAR STOCK ==========
                print("DEBUG: Procesando items_validados...")
                for item in items_validados:
                    print(f"DEBUG: Procesando item: {item}")
                    
                    if item['tipo'] == "servicio":
                        FacturaServicio.objects.create(
                            factura=factura,
                            descripcion=item['descripcion'],
                            cantidad=item['cantidad'],
                            precio_unitario=item['precio'],
                        )
                    else:
                        FacturaInsumo.objects.create(
                            factura=factura,
                            insumo=item['insumo'],
                            descripcion=item['descripcion'],
                            cantidad=item['cantidad'],
                            precio_unitario=item['precio'],
                        )
                        
                        if item['insumo']:
                            print(f"DEBUG: Descontando stock de {item['insumo'].nombre} x{item['cantidad']}")
                            descontar_stock_insumo(item['descripcion'], item['cantidad'])
                        else:
                            print(f"DEBUG: item['insumo'] es None, intentando descontar por descripción: {item['descripcion']}")
                            descontar_stock_insumo(item['descripcion'], item['cantidad'])
                            
                    total_items += 1

                # ========== VALIDACIÓN DE ITEMS ==========
                if total_items == 0:
                    if not orden_id or not orden:
                        messages.error(request, "Debe agregar al menos un producto a la factura")
                        return redirect("factura_emitir")
                    else:
                        # ===== RECALCULAR TOTALES FINALES =====
                        factura.recalcular_totales(guardar=True)
                        print(f"Total general de la factura: {factura.total_general}")  # DEBUG
                        
                        data_sefin = generar_json_sefin(factura)
                        guardar_json_sefin(factura, data_sefin)
                        
                        if orden_id and orden:
                            orden.factura_generada = True
                            orden.factura = factura
                            orden.estado = 'facturado'
                            orden.save(update_fields=['factura_generada', 'factura', 'estado'])
                        
                        # ===== CREAR MOVIMIENTO FINANCIERO (DESPUÉS DE RECALCULAR) =====
                        if factura.total_general > 0:
                            movimiento = crear_movimiento_factura(factura, request.user)
                            if movimiento:
                                print(f"Movimiento creado con monto: {movimiento.monto}")
                            else:
                                print("No se pudo crear el movimiento")
                        else:
                            print("Total general es 0, no se crea movimiento")
                        
                        messages.success(request, f"Factura {factura.numero_formateado} creada correctamente desde OT")
                        return redirect("factura_ver", factura_id=factura.id)
                else:
                    # ===== RECALCULAR TOTALES FINALES =====
                    factura.recalcular_totales(guardar=True)
                    print(f"Total general de la factura: {factura.total_general}")  # DEBUG
                    
                    data_sefin = generar_json_sefin(factura)
                    guardar_json_sefin(factura, data_sefin)
                    
                    if orden_id and orden:
                        orden.factura_generada = True
                        orden.factura = factura
                        orden.estado = 'facturado'
                        orden.save(update_fields=['factura_generada', 'factura', 'estado'])
                    
                        from orden_trabajo.services import ComisionService
                        ComisionService.procesar_comisiones_orden(orden)
                    
                    # ===== CREAR MOVIMIENTO FINANCIERO (DESPUÉS DE RECALCULAR) =====
                    if factura.total_general > 0:
                        movimiento = crear_movimiento_factura(factura, request.user)
                        if movimiento:
                            print(f"Movimiento creado con monto: {movimiento.monto}")
                        else:
                            print("No se pudo crear el movimiento")
                    else:
                        print("Total general es 0, no se crea movimiento")
                    
                    messages.success(request, f"Factura {factura.numero_formateado} creada")
                    return redirect("factura_ver", factura_id=factura.id)
                    
            except (ValueError, TypeError) as e:
                print("ERROR:", str(e))
                messages.error(request, f"Error al crear factura: {str(e)}")
        else:
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"Error en {field}: {error}")
            if item_formset.errors:
                for error in item_formset.errors:
                    if error:
                        messages.error(request, f"Error en items: {error}")
            if not form.errors and not item_formset.errors:
                messages.error(request, "Corrija los errores del formulario")

    else:
        form = FacturaEmitirForm(initial=initial_data)
        item_formset = ItemFacturaFormSet(prefix="items")

    clientes = Cliente.objects.filter(is_active=True).order_by('nombre')

    return render(request, "factura/factura_emitir.html", {
        'form': form,
        'item_formset': item_formset,
        'fecha_actual': timezone.localdate().isoformat(),
        'proximo_numero': numero_formateado,
        'timbrado_actual': timbrado_actual,
        'valido_hasta': valido_hasta,
        'insumos': Insumo.objects.filter(grupo='insumo_venta', is_active=True),
        'clientes': clientes,
        'orden_id': orden_id,
        'servicios_precargados': servicios_precargados,
        'cliente_precargado': cliente_precargado,
    })


def generar_json_sefin(factura):
    data = {
        "factura": {
            "numero": factura.numero_formateado,
            "fecha": str(factura.fecha),
            "timbrado": factura.timbrado,
            "establecimiento": factura.establecimiento,
            "punto_emision": factura.punto_emision,
            "estado": factura.estado,
        },
        "cliente": {
            "nombre": factura.cliente.nombre if factura.cliente else "",
            "documento": factura.cliente.numero_documento if factura.cliente else "",
        },
        "totales": {
            "total": float(factura.total_general),
        },
        "items": []
    }

    for s in factura.servicios.all():
        data["items"].append({
            "tipo": "servicio",
            "descripcion": s.descripcion,
            "cantidad": float(s.cantidad),
            "precio": float(s.precio_unitario),
        })

    for i in factura.insumos.all():
        data["items"].append({
            "tipo": "insumo",
            "descripcion": i.descripcion,
            "cantidad": float(i.cantidad),
            "precio": float(i.precio_unitario),
        })

    return data


def guardar_json_sefin(factura, data):
    carpeta = os.path.join(settings.BASE_DIR, "sefin")

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    nombre_archivo = f"factura_{factura.id}.json"
    ruta = os.path.join(carpeta, nombre_archivo)

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


@login_required
@permission_required('seguridad.ver_facturas', raise_exception=True)
def factura_ver(request, factura_id):
    factura = get_object_or_404(
        Factura.objects.prefetch_related("servicios", "insumos"),
        pk=factura_id
    )

    def get_config(clave, default=""):
        try:
            return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
        except ConfiguracionSistema.DoesNotExist:
            return default

    config = {
        "nombre_taller": get_config("nombre_taller"),
        "ruc_taller": get_config("ruc_taller"),
        "direccion_taller": get_config("direccion_taller"),
    }
    ruta_json = os.path.join(settings.BASE_DIR, "sefin", f"factura_{factura.id}.json")

    json_data = None

    if os.path.exists(ruta_json):
        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                json_data = json.load(f)
        except Exception:
            json_data = None
    context = {
        "factura": factura,
        "config": config,
        "json_data": json_data,
    }

    return render(request, "factura/factura_ver.html", context)


@login_required
@permission_required('seguridad.editar_facturas', raise_exception=True)
@transaction.atomic
def factura_editar(request, factura_id):
    from decimal import Decimal
    
    factura = get_object_or_404(Factura, pk=factura_id)

    if factura.estado != Factura.Estado.ACTIVA:
        messages.error(request, "No se puede editar una factura anulada")
        return redirect("factura_ver", factura_id=factura.id)

    if request.method == "POST":
        # ========== REPONER STOCK ORIGINAL ANTES DE EDITAR ==========
        for insumo_factura in factura.insumos.all():
            reponer_stock_insumo(insumo_factura.descripcion, insumo_factura.cantidad)
        
        form = FacturaEmitirForm(request.POST, instance=factura)
        srv_fs = ServicioFormSet(request.POST, prefix="srv")
        ins_fs = InsumoFormSet(request.POST, prefix="ins")

        # ========== VALIDAR STOCK DE NUEVOS INSUMOS ==========
        errores_stock = []
        
        for d in ins_fs.cleaned_data:
            if d and not d.get("DELETE"):
                descripcion = d.get("descripcion", "")
                cantidad = d.get("cantidad", 0)
                
                ok, insumo, cant = validar_stock_insumo(descripcion, cantidad)
                if not ok:
                    errores_stock.append(
                        f"{insumo.nombre}: necesita {cant} {insumo.unidad}, "
                        f"stock disponible: {insumo.stock_actual} {insumo.unidad}"
                    )

        if errores_stock:
            for error in errores_stock:
                messages.error(request, f"Stock insuficiente: {error}")
            return redirect("factura_editar", factura_id=factura.id)

        if form.is_valid() and srv_fs.is_valid() and ins_fs.is_valid():
            factura = form.save(commit=False)
            cliente_id = request.POST.get("cliente")
            if cliente_id:
                try:
                    factura.cliente = Cliente.objects.get(id=cliente_id)
                except Cliente.DoesNotExist:
                    factura.cliente = None

            factura.save()

            factura.servicios.all().delete()
            factura.insumos.all().delete()

            for d in srv_fs.cleaned_data:
                if d and not d.get("DELETE"):
                    FacturaServicio.objects.create(factura=factura, **d)

            # ========== CREAR NUEVOS INSUMOS Y DESCONTAR STOCK ==========
            for d in ins_fs.cleaned_data:
                if d and not d.get("DELETE"):
                    FacturaInsumo.objects.create(factura=factura, **d)
                    descontar_stock_insumo(d.get("descripcion", ""), d.get("cantidad", 0))

            factura.recalcular_totales(guardar=True)
            data_sefin = generar_json_sefin(factura)
            guardar_json_sefin(factura, data_sefin)
            messages.success(request, "Factura actualizada")
            return redirect("factura_ver", factura_id=factura.id)

        messages.error(request, "Errores en el formulario")

    else:
        form = FacturaEmitirForm(instance=factura)

        srv_fs = ServicioFormSet(
            prefix="srv",
            initial=[{"descripcion": s.descripcion, "cantidad": s.cantidad, "precio_unitario": s.precio_unitario}
                     for s in factura.servicios.all()]
        )

        ins_fs = InsumoFormSet(
            prefix="ins",
            initial=[{"descripcion": i.descripcion, "cantidad": i.cantidad, "precio_unitario": i.precio_unitario}
                     for i in factura.insumos.all()]
        )

    return render(request, "factura/factura_editar.html", {
        "form": form,
        "srv_fs": srv_fs,
        "ins_fs": ins_fs,
        "factura": factura
    })


@login_required
@permission_required('seguridad.ver_facturas', raise_exception=True)
def factura_lista(request):
    
    # Actualizar estados de notas de crédito pendientes (más de 24 horas)
    notas_pendientes = NotaCredito.objects.filter(estado=NotaCredito.Estado.PENDIENTE)
    for nota in notas_pendientes:
        nota.actualizar_estado_automatico()
        print(f"Nota {nota.id}: creada {nota.created_at}, nueva estado: {nota.estado}")
    
    # Anular facturas vencidas
    Factura.anular_facturas_vencidas()
    
    facturas = Factura.objects.select_related('cliente').order_by("-fecha", "-id")

    q_id = request.GET.get('id', '')
    if q_id and q_id.isdigit():
        facturas = facturas.filter(id=int(q_id))
    
    fecha_desde = request.GET.get('fecha_desde')
    if fecha_desde:
        facturas = facturas.filter(fecha__gte=fecha_desde)
    
    fecha_hasta = request.GET.get('fecha_hasta')
    if fecha_hasta:
        facturas = facturas.filter(fecha__lte=fecha_hasta)
    
    estado = request.GET.get('estado')
    if estado:
        facturas = facturas.filter(estado=estado)
    
    paginator = Paginator(facturas, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    
    qs_copy = request.GET.copy()
    qs_copy.pop('page', None)
    qs_no_page = qs_copy.urlencode()
    
    return render(request, "factura/factura_lista.html", {
        "facturas": page_obj,
        "q_id": q_id,
        "q_estado": estado,
        "qs_no_page": qs_no_page,
    })


@login_required
@permission_required('seguridad.editar_facturas', raise_exception=True)
def factura_marcar_entregada(request, factura_id):
    if request.method == 'POST':
        factura = get_object_or_404(Factura, pk=factura_id)
        factura.entregada = True
        factura.save(update_fields=['entregada'])
        messages.success(request, f"Factura #{factura.numero_formateado} marcada como entregada")
    return redirect('factura_lista')


@login_required
@permission_required('seguridad.anular_facturas', raise_exception=True)
@transaction.atomic
def factura_anular(request, factura_id):
    from decimal import Decimal
    
    factura = get_object_or_404(Factura, pk=factura_id)

    if not factura.puede_anular:
        messages.error(request, "No se puede anular la factura. Superó el límite de 48 horas")
        return redirect("factura_ver", factura_id=factura.id)

    if request.method == "POST":
        motivo = request.POST.get('motivo', '').strip()
        
        if not motivo:
            messages.error(request, "El motivo de anulación es obligatorio")
            return redirect("factura_lista")
        
        try:
            # ========== REPONER STOCK DE INSUMOS ANULADOS ==========
            for insumo_factura in factura.insumos.all():
                reponer_stock_insumo(insumo_factura.descripcion, insumo_factura.cantidad)
            
            factura.anular(motivo=motivo, usuario=request.user)
            
            # ========== ANULAR MOVIMIENTO FINANCIERO ==========
            anular_movimiento_factura(factura, request.user)
            
            messages.success(request, f"Factura #{factura.numero_formateado} anulada")
        except ValidationErr as e:
            messages.error(request, str(e))
        
        return redirect("factura_lista")
    
    return redirect("factura_lista")


@login_required
@permission_required('seguridad.imprimir_facturas', raise_exception=True)
def factura_imprimir(request, factura_id):
    factura = get_object_or_404(
        Factura.objects.prefetch_related("servicios", "insumos", "cliente"),
        pk=factura_id
    )
    
    def get_config(clave, default=""):
        try:
            return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
        except ConfiguracionSistema.DoesNotExist:
            return default
    
    config = {
        "nombre_taller": get_config("nombre_taller", "TALLER AUTOMOTRIZ"),
        "ruc_taller": get_config("ruc_taller", "—"),
        "direccion_taller": get_config("direccion_taller", "—"),
        "telefono_taller": get_config("telefono_taller", "—"),
    }
    
    marca = "ANULADA" if factura.estado == Factura.Estado.ANULADA else ""
    
    return render(request, "factura/factura_imprimir.html", {
        "factura": factura,
        "marca": marca,
        "config": config,
    })


@login_required
@permission_required('seguridad.reimprimir_facturas', raise_exception=True)
def factura_reimprimir(request, factura_id):
    factura = get_object_or_404(
        Factura.objects.prefetch_related("servicios", "insumos", "cliente"),
        pk=factura_id
    )
    
    def get_config(clave, default=""):
        try:
            return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
        except ConfiguracionSistema.DoesNotExist:
            return default
    
    config = {
        "nombre_taller": get_config("nombre_taller", "TALLER AUTOMOTRIZ"),
        "ruc_taller": get_config("ruc_taller", "—"),
        "direccion_taller": get_config("direccion_taller", "—"),
        "telefono_taller": get_config("telefono_taller", "—"),
    }
    
    if factura.estado == Factura.Estado.ANULADA:
        marca = "ANULADA - COPIA"
    else:
        marca = "COPIA"
    
    return render(request, "factura/factura_imprimir.html", {
        "factura": factura,
        "marca": marca,
        "config": config,
    })


@login_required
@permission_required('seguridad.ver_facturas', raise_exception=True)
def factura_consultar(request):
    numero = (request.GET.get("numero") or "").strip()
    factura = None

    if numero.isdigit():
        factura = Factura.objects.filter(id=int(numero)).first()

    return render(request, "factura/factura_consultar.html", {
        "factura": factura,
        "numero": numero
    })


@login_required
@permission_required('seguridad.anular_facturas', raise_exception=True)
@transaction.atomic
def nota_credito_emitir(request, factura_id):
    
    factura = get_object_or_404(
        Factura.objects.prefetch_related("servicios", "insumos", "notas_credito"),
        pk=factura_id
    )

    if factura.estado == Factura.Estado.ANULADA:
        messages.info(request, "No se puede generar Nota de Crédito porque la factura está anulada")
        return redirect("factura_lista")

    if factura.tiene_nota_credito:
        messages.info(request, "Esta factura ya tiene una Nota de Crédito activa")
        return redirect("factura_ver", factura_id=factura.id)

    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "El motivo de la Nota de Crédito es obligatorio")
            return redirect("nota_credito_emitir", factura_id=factura.id)

        try:
            total = Decimal("0")
            total_factura = factura.total_general
            cantidad_items = 0

            # SERVICIOS DE LA FACTURA
            for s in factura.servicios.all():
                cantidad = Decimal(str(request.POST.get(f"serv_{s.id}", "0") or "0"))
                if cantidad <= 0:
                    continue
                if cantidad > Decimal(str(s.cantidad)):
                    cantidad = Decimal(str(s.cantidad))
                total += cantidad * s.precio_unitario
                cantidad_items += 1

            # INSUMOS DE LA FACTURA
            for i in factura.insumos.all():
                cantidad = Decimal(str(request.POST.get(f"ins_{i.id}", "0") or "0"))
                if cantidad <= 0:
                    continue
                if cantidad > Decimal(str(i.cantidad)):
                    cantidad = Decimal(str(i.cantidad))
                total += cantidad * i.precio_unitario
                cantidad_items += 1

            if cantidad_items == 0 or total <= 0:
                messages.error(request, "Debe seleccionar al menos un ítem para la Nota de Crédito")
                return redirect("nota_credito_emitir", factura_id=factura.id)

            # ===== CREAR LA NOTA =====
            es_total = total >= total_factura
            
            nota = NotaCredito.objects.create(
                factura=factura,
                motivo=motivo,
                tipo="TOTAL" if es_total else "PARCIAL"
            )

            # ===== CREAR LOS DETALLES DE LA NOTA =====
            # SERVICIOS DE LA FACTURA
            for s in factura.servicios.all():
                cantidad = Decimal(str(request.POST.get(f"serv_{s.id}", "0") or "0"))
                if cantidad <= 0:
                    continue
                if cantidad > Decimal(str(s.cantidad)):
                    cantidad = Decimal(str(s.cantidad))

                NotaCreditoDetalle.objects.create(
                    nota=nota,
                    descripcion=s.descripcion,
                    cantidad=cantidad,
                    precio_unitario=s.precio_unitario
                )

            # INSUMOS DE LA FACTURA - REPONER STOCK
            for i in factura.insumos.all():
                cantidad = Decimal(str(request.POST.get(f"ins_{i.id}", "0") or "0"))
                if cantidad <= 0:
                    continue
                if cantidad > Decimal(str(i.cantidad)):
                    cantidad = Decimal(str(i.cantidad))

                NotaCreditoDetalle.objects.create(
                    nota=nota,
                    descripcion=i.descripcion,
                    cantidad=cantidad,
                    precio_unitario=i.precio_unitario
                )
                
                # Reponer stock del insumo devuelto
                reponer_stock_insumo(i.descripcion, cantidad)

            # ===== CALCULAR TOTALES DE LA NOTA =====
            if factura.iva == 10:
                nota.total_iva = total / Decimal("11")
            elif factura.iva == 5:
                nota.total_iva = total / Decimal("21")
            else:
                nota.total_iva = Decimal("0")

            nota.subtotal = total - nota.total_iva
            nota.total_general = total
            nota.save(update_fields=["subtotal", "total_iva", "total_general"])
            
            # ===== CREAR MOVIMIENTO FINANCIERO PARA LA NOTA DE CRÉDITO =====
            #if nota.total_general > 0:
            #    crear_movimiento_nota_credito(nota, request.user)
            
            # ===== ACTUALIZAR FACTURA =====
            factura.fecha_nota_credito = timezone.now()
            factura.save(update_fields=['fecha_nota_credito'])
            
            if es_total:
                messages.success(request, f"Nota de Crédito TOTAL #{nota.numero_formateado} generada")
            else:
                messages.success(request, f"Nota de Crédito PARCIAL #{nota.numero_formateado} generada")

            return redirect("nota_credito_ver", nota_id=nota.id)

        except Exception as e:
            print("ERROR NOTA CREDITO:", str(e))
            messages.error(request, f"Error al generar Nota de Crédito: {str(e)}")
            return redirect("nota_credito_emitir", factura_id=factura.id)

    return render(request, "factura/nota_credito_emitir.html", {
        "factura": factura,
        "fecha_actual": timezone.localdate(),
    })


@login_required
@permission_required('seguridad.ver_facturas', raise_exception=True)
def nota_credito_ver(request, nota_id):
    nota = get_object_or_404(
        NotaCredito.objects.select_related('factura__cliente').prefetch_related('detalles'),
        pk=nota_id
    )
    
    def get_config(clave, default=""):
        try:
            return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
        except ConfiguracionSistema.DoesNotExist:
            return default
    
    config = {
        "nombre_taller": get_config("nombre_taller", "Taller Automotriz"),
        "ruc_taller": get_config("ruc_taller", "—"),
        "direccion_taller": get_config("direccion_taller", "—"),
    }
    
    # Determinar si es total o parcial
    es_total = nota.total_general >= nota.factura.total_general
    
    return render(request, "factura/nota_credito_ver.html", {
        "nota": nota,
        "config": config,
        "es_total": es_total,
    })


@login_required
@permission_required('seguridad.ver_facturas', raise_exception=True)
def nota_credito_lista(request):
    notas = NotaCredito.objects.select_related('factura__cliente').prefetch_related('detalles').order_by("-id")
    
    q = request.GET.get('q', '')
    if q:
        notas = notas.filter(
            Q(id__icontains=q) | 
            Q(factura__id__icontains=q) |
            Q(factura__numero__icontains=q)
        )
    
    fecha_desde = request.GET.get('fecha_desde')
    if fecha_desde:
        notas = notas.filter(fecha__gte=fecha_desde)
    
    fecha_hasta = request.GET.get('fecha_hasta')
    if fecha_hasta:
        notas = notas.filter(fecha__lte=fecha_hasta)
    
    paginator = Paginator(notas, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    
    return render(request, "factura/nota_credito_lista.html", {
        "notas_credito": page_obj,
    })


@login_required
@permission_required('seguridad.anular_facturas', raise_exception=True)
def nota_credito_anular(request, nota_id):
    if request.method == 'POST':
        nota = get_object_or_404(NotaCredito, pk=nota_id)
        nota.estado = NotaCredito.Estado.ANULADA
        nota.save(update_fields=['estado'])
        messages.success(request, f"Nota de Crédito {nota.numero_formateado} anulada")
    return redirect('nota_credito_lista')


@login_required
@permission_required('seguridad.imprimir_facturas', raise_exception=True)
def nota_credito_imprimir(request, nota_id):
    nota = get_object_or_404(
        NotaCredito.objects.select_related('factura__cliente'),
        pk=nota_id
    )
    
    def get_config(clave, default=""):
        try:
            return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
        except ConfiguracionSistema.DoesNotExist:
            return default
    
    config = {
        "nombre_taller": get_config("nombre_taller", "TALLER AUTOMOTRIZ"),
        "ruc_taller": get_config("ruc_taller", "—"),
        "direccion_taller": get_config("direccion_taller", "—"),
        "telefono_taller": get_config("telefono_taller", "—"),
    }
    
    return render(request, "factura/nota_credito_imprimir.html", {
        "nota": nota,
        "config": config,
    })


@login_required
@permission_required('seguridad.anular_facturas', raise_exception=True)
def nota_credito_factura(request):
    """Vista para seleccionar una factura sin nota de crédito"""
    facturas = Factura.objects.filter(
        estado=Factura.Estado.ACTIVA,
        fecha_nota_credito__isnull=True
    ).exclude(
        id__in=NotaCredito.objects.values_list('factura_id', flat=True)
    ).select_related('cliente').order_by('-fecha', '-id')
    
    # Filtros
    q = request.GET.get('q', '')
    if q:
        if q.isdigit():
            facturas = facturas.filter(id=int(q))
        else:
            facturas = facturas.filter(
                Q(cliente__nombre__icontains=q) |
                Q(cliente__numero_documento__icontains=q)
            )
    
    return render(request, "factura/nota_credito_factura.html", {
        "facturas": facturas,
    })


# BUSCADORES
@login_required
def buscar_clientes_autocomplete(request):
    query = request.GET.get('q', '')

    clientes = Cliente.objects.filter(is_active=True)

    if query:
        clientes = clientes.filter(
            Q(numero_documento__icontains=query) |
            Q(nombre__icontains=query)
        )[:10]
    else:
        clientes = clientes[:10]

    data = [{
        'id': c.id,
        'text': f"{c.numero_documento} - {c.nombre}",
        'documento': c.numero_documento,
        'nombre': c.nombre,
        'telefono': c.telefono or '',
        'direccion': c.direccion or ''
    } for c in clientes]

    return JsonResponse(data, safe=False)


@login_required
def buscar_insumos_venta(request):
    query = request.GET.get('q', '').strip()
    
    insumos = Insumo.objects.filter(grupo='insumo_venta', is_active=True)
    
    if query:
        insumos = insumos.filter(
            Q(nombre__icontains=query) |
            Q(codigo_completo__icontains=query) |
            Q(id__icontains=query)
        )
    
    insumos = insumos.order_by('nombre')[:20]
    
    data = [{
        'id': i.id,
        'codigo': i.codigo_completo,
        'nombre': i.nombre,
        'precio_venta': float(i.precio_venta) if hasattr(i, 'precio_venta') else float(i.costo_unitario),
        'costo_unitario': float(i.costo_unitario),
        'stock_actual': float(i.stock_actual),
        'unidad': i.unidad
    } for i in insumos]
    
    return JsonResponse(data, safe=False)