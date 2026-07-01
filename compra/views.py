# pylint: disable=E1101,no-member,broad-exception-caught
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

from datetime import date, timezone
from xml.dom import ValidationErr
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError

from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils.translation import gettext_lazy as _
from proveedor.models import Proveedor
from .forms import (
    CompraEditarForm,
    CompraForm,
)

from .models import (
    BitacoraCompra,
    Compra,
    CompraProducto,
)

from insumo.models import Insumo
from .utils import get_config


# ==========================================================
# QUERYSET BASE
# ==========================================================

def get_qs_compras(
    request,
    solo_pendientes=False
):

    qs = Compra.objects.select_related(

        "proveedor",

    ).prefetch_related(
        "detalles"
    )

    # ======================================================
    # SOLO PENDIENTES
    # ======================================================

    if solo_pendientes:

        qs = qs.filter(
            estado="pendiente"
        )

    # ======================================================
    # BUSQUEDA
    # ======================================================

    q = request.GET.get(
        "q",
        ""
    ).strip()

    if q:

        qs = qs.filter(

            Q(id__icontains=q)

            | Q(
                proveedor__razon_social__icontains=q
            )

            | Q(
                proveedor__ruc__icontains=q
            )
        )

    # ======================================================
    # ESTADO
    # ======================================================

    estado = request.GET.get(
        "estado"
    )

    if estado and not solo_pendientes:

        qs = qs.filter(
            estado=estado
        )

    # ======================================================
    # FECHAS
    # ======================================================

    desde = request.GET.get(
        "desde"
    )

    hasta = request.GET.get(
        "hasta"
    )

    if desde:

        qs = qs.filter(
            fecha_emision__date__gte=desde
        )

    if hasta:

        qs = qs.filter(
            fecha_emision__date__lte=hasta
        )

    return qs.order_by(
        "-fecha_emision"
    )


# ==========================================================
# LISTA
# ==========================================================

@login_required
@permission_required("seguridad.ver_compras",raise_exception=True)
def compra_lista(request):
    qs = get_qs_compras(request)
    paginator = Paginator(
        qs,
        25
    )
    page_number = request.GET.get(
        "page"
    )
    compras = paginator.get_page(
        page_number
    )

    context = {
        "compras": compras,
        "estados": (
            Compra.ESTADO_CHOICES
        ),

        "qs_no_page": (
            request.GET.urlencode()
            .replace(
                f"page={compras.number}&",
                ""
            )
            .replace(
                f"&page={compras.number}",
                ""
            )
        ),
    }
    return render(

        request, "compras/compra_lista.html", context
    )


# ==========================================================
# CAMBIAR ESTADOS
# ==========================================================

@login_required
@permission_required("seguridad.cambiar_estado_compras",raise_exception=True)
def compra_cambiar_estados(request):
    qs = get_qs_compras(
        request,
        solo_pendientes=True
    )
    paginator = Paginator(
        qs,
        25
    )
    page_number = request.GET.get(
        "page"
    )
    compras = paginator.get_page(
        page_number
    )
    context = {
        "compras": compras,
        "qs_no_page": (
            request.GET.urlencode()
            .replace(
                f"page={compras.number}&",
                ""
            )
            .replace(
                f"&page={compras.number}",
                ""
            )
        ),
    }

    return render(request, "compras/compra_cambiar_estados.html", context)


# ==========================================================
# VER DETALLE
# ==========================================================
@login_required
@permission_required("seguridad.ver_compras", raise_exception=True)
def compra_ver(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related(
            "proveedor",
        ).prefetch_related(
            "detalles"
        ),
        id=compra_id
    )


    # ========== OBTENER USUARIOS DE BITÁCORA ==========
    usuario_creacion = None
    usuario_actualizacion = None
    ultima_actualizacion = compra.fecha_emision
    
    # Obtener todas las entradas de bitácora ordenadas por fecha
    bitacoras = compra.bitacora.all().order_by('fecha')
    
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

    if compra.estado in ['aprobado', 'rechazado', 'recibido']:
        messages.info(request, f"La compra con estado {compra.get_estado_display().upper()} ya no puede ser modificado")


    if compra.estado == "recibido" and not compra.factura_pdf:
        messages.info(request, "Esta compra no tiene factura PDF cargada")


    # Calcular subtotal basado en recibido si corresponde
    subtotal_real = Decimal('0.00')
    for detalle in compra.detalles.all():
        if compra.estado == 'recibido' and detalle.cantidad_recibida > 0:
            subtotal_producto = detalle.cantidad_recibida * detalle.producto.costo_unitario
            subtotal_real += subtotal_producto
            # Guardar el subtotal calculado en el objeto detalle para usarlo en el template
            detalle.subtotal_calculado = subtotal_producto
        else:
            subtotal_producto = detalle.subtotal
            subtotal_real += subtotal_producto
            detalle.subtotal_calculado = subtotal_producto
    
    # Calcular base imponible, IVA y total basado en el subtotal real
    base_real = max(subtotal_real - compra.descuento, Decimal('0.00'))
    iva_real = base_real * (compra.iva_porcentaje / Decimal('100'))
    total_real = base_real + iva_real


    return render(request, "compras/compra_ver.html", {
        "compra": compra,
        "usuario_creacion": usuario_creacion,
        "usuario_actualizacion": usuario_actualizacion,
        "ultima_actualizacion": ultima_actualizacion,
        "subtotal_real": subtotal_real,
        "base_real": base_real,
        "iva_real": iva_real,
        "total_real": total_real,
    })


@login_required
@permission_required("seguridad.ver_compras", raise_exception=True)
def compra_ver_pdf(request, compra_id):
    compra = get_object_or_404(Compra, id=compra_id)
    
    response = HttpResponse(compra.factura_pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="factura_{}.pdf"'.format(compra.id)
    return response


# ==========================================================
# CREAR
# ==========================================================

@login_required
@permission_required("seguridad.agregar_compras",raise_exception=True)
def compra_crear(request):
    if request.method == "POST":
        form = CompraForm(request.POST)
        
        if form.is_valid():
            with transaction.atomic():
                compra = form.save(commit=False)
                compra.condicion_pago = request.POST.get('condicion_pago', 'contado')
                compra.save()

                # ==========================================
                # PRODUCTOS
                # ==========================================
                i = 0
                productos_agregados = 0
                while f"productos[{i}][producto_id]" in request.POST:
                    producto_id = request.POST.get(f"productos[{i}][producto_id]", "").strip()
                    cantidad_str = request.POST.get(f"productos[{i}][cantidad]", "0").strip()

                    if producto_id and cantidad_str:
                        try:
                            cantidad = Decimal(cantidad_str)
                            if cantidad > 0:
                                producto = Insumo.objects.get(id=producto_id)
                                CompraProducto.objects.create(
                                    compra=compra,
                                    producto=producto,
                                    cantidad=cantidad,
                                )
                                productos_agregados += 1
                        except Exception:
                            pass
                    i += 1
                
                # ==========================================
                # VALIDAR PRODUCTOS
                # ==========================================
                if productos_agregados == 0:
                    compra.delete()
                    messages.error(request, "Debe agregar al menos un producto a la orden de compra.")
                    productos = Insumo.objects.filter(is_active=True).order_by("nombre")
                    return render(request, "compras/compra_crear.html", {
                        "form": form,
                        "productos_disponibles": productos,
                    })

                # ==========================================
                # TOTALES
                # ==========================================
                compra.actualizar_totales()
                compra.save(update_fields=["subtotal_productos", "iva_monto", "total"])

                # ==========================================
                # BITACORA
                # ==========================================
                BitacoraCompra.registrar(compra, "CREACIÓN", "Orden creada", request.user)

                messages.success(request, f"Orden de compra #{compra.id} creada")
                return redirect("compra_ver", compra_id=compra.id)
        else:
            # ==========================================
            # SOLO mostrar errores que NO son de campos específicos
            # Los errores de campos se muestran automáticamente en el HTML con {{ form.campo.errors }}
            # ==========================================
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = CompraForm()

    productos = Insumo.objects.filter(is_active=True).order_by("nombre")

    return render(request, "compras/compra_crear.html", {
        "form": form,
        "productos_disponibles": productos,
    })


# ==========================================================
# EDITAR
# ==========================================================

@login_required
@permission_required("seguridad.editar_compras", raise_exception=True)
def compra_editar(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related(
            "proveedor",
        ).prefetch_related(
            "detalles__producto"
        ),
        id=compra_id
    )
    
    if not compra.es_editable:
        messages.error(request, "Esta compra ya no es editable")
        return redirect("compra_ver", compra_id=compra.id)
    
    if request.method == "POST":
        form = CompraEditarForm(request.POST, instance=compra)

        
        # Limpiar errores de validación de productos del formulario
        if 'descripcion' in form.errors:
            errores_descripcion = []
            for error in form.errors['descripcion']:
                if "debe tener al menos un producto" not in str(error):
                    errores_descripcion.append(error)
            if errores_descripcion:
                form.errors['descripcion'] = errores_descripcion
            else:
                del form.errors['descripcion']
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardar campos del formulario
                    compra = form.save()
                    
                    # 2. PROCESAR PRODUCTOS EXISTENTES (actualizar cantidades)
                    for key, value in request.POST.items():
                        if key.startswith('cantidad_') and key != 'cantidadInput':
                            try:
                                detalle_id = int(key.replace('cantidad_', ''))
                                nueva_cantidad = Decimal(value)
                                if nueva_cantidad > 0:
                                    detalle = CompraProducto.objects.get(id=detalle_id, compra=compra)
                                    print(f"Actualizando {detalle.producto.nombre}: {detalle.cantidad} -> {nueva_cantidad}")
                                    detalle.cantidad = nueva_cantidad
                                    detalle.save()
                            except Exception as e:
                                print(f"Error: {e}")
                    
                    # 3. ELIMINAR PRODUCTOS MARCADOS
                    eliminados = request.POST.getlist('productos_eliminados[]')
                    print(f"productos_eliminados[] = {eliminados}")
                    
                    for detalle_id_str in eliminados:
                        if detalle_id_str:
                            try:
                                detalle_id = int(detalle_id_str)
                                detalle = CompraProducto.objects.get(id=detalle_id, compra=compra)
                                print(f"Eliminando: {detalle.producto.nombre}")
                                detalle.delete()
                            except Exception as e:
                                print(f"Error eliminando {detalle_id_str}: {e}")
                    
                    # 4. AGREGAR PRODUCTOS NUEVOS 
                    productos_agregados = 0
                    
                    import re
                    
                    for key, value in request.POST.items():
                        # Buscar patrón: productos_nuevos[ cualquier número ][producto_id]
                        match = re.match(r'productos_nuevos\[(\d+)\]\[producto_id\]', key)
                        if match:
                            idx = match.group(1)
                            producto_id = value
                            cantidad_key = f'productos_nuevos[{idx}][cantidad]'
                            cantidad_str = request.POST.get(cantidad_key)
                            
                            print(f"Procesando índice {idx}: producto_id={producto_id}, cantidad={cantidad_str}")
                            
                            if producto_id and cantidad_str:
                                try:
                                    cantidad = Decimal(cantidad_str)
                                    if cantidad > 0:
                                        producto = Insumo.objects.get(id=int(producto_id))
                                        # Verificar que no exista ya
                                        if not CompraProducto.objects.filter(compra=compra, producto=producto).exists():
                                            nuevo_detalle = CompraProducto.objects.create(
                                                compra=compra,
                                                producto=producto,
                                                cantidad=cantidad
                                            )
                                            productos_agregados += 1
                                            print(f"Agregado: {producto.nombre} x{cantidad} (ID: {nuevo_detalle.id})")
                                        else:
                                            print(f"Producto ya existe: {producto.nombre}")
                                except Exception as e:
                                    print(f"Error: {e}")
                    
                    print(f"\n  Total productos nuevos agregados: {productos_agregados}")
                    
                    # 5. Actualizar totales
                    compra.actualizar_totales()
                    compra.save(update_fields=["subtotal_productos", "iva_monto", "total"])
                    
                    # 6. Verificar que haya al menos un producto
                    cantidad_final = compra.detalles.count()
                    
                    if cantidad_final == 0:
                        raise ValidationError("La compra debe tener al menos un producto")
                    
                    BitacoraCompra.registrar(compra, "EDICIÓN", "Compra actualizada", request.user)
                    messages.success(request, f"Orden de compra #{compra.id} actualizada")
                    return redirect("compra_ver", compra_id=compra.id)
                    
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error al actualizar: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        form = CompraEditarForm(instance=compra)
    
    productos_disponibles = Insumo.objects.filter(is_active=True).order_by('nombre')
    
    return render(request, "compras/compra_editar.html", {
        "form": form,
        "compra": compra,
        "productos_disponibles": productos_disponibles,
    })

# ==========================================================
# APROBAR
# ==========================================================

@login_required
@permission_required("seguridad.cambiar_estado_compras", raise_exception=True)
def compra_aprobar(request, compra_id):
    compra = get_object_or_404(Compra, id=compra_id)
    if compra.estado == "pendiente":
        compra.estado = "aprobado"
        compra.save(update_fields=["estado"])

        BitacoraCompra.registrar(
            compra,
            "APROBADA",
            "Orden aprobada",
            request.user
        )
        
        
        messages.success(request, f"Orden de compra #{compra.id} aprobada")
    else:
        messages.error(
            request,
            _("Solo se pueden aprobar compras pendientes")
        )
    return redirect("compra_cambiar_estados")


# ==========================================================
# RECHAZAR
# ==========================================================

@login_required
@permission_required("seguridad.cambiar_estado_compras",raise_exception=True)
def compra_rechazar(request,compra_id):
    compra = get_object_or_404(
        Compra,
        id=compra_id
    )
    if compra.estado in [
        "pendiente",
        "aprobado",
    ]:
        compra.estado = "rechazado"
        compra.save(
            update_fields=["estado"]
        )
        BitacoraCompra.registrar(
            compra,
            "RECHAZADA",
            "Orden rechazada",
            request.user
        )
        messages.success(request, f"Orden de compra #{compra.id} rechazada")
    else:
        messages.error(
            request,
            _(
                "No se puede RECHAZAR esta compra"
            )
        )

    return redirect(
        "compra_cambiar_estados"
    )


# ==========================================================
# RECIBIR
# ==========================================================

@login_required
@permission_required("seguridad.recibir_compras", raise_exception=True)
def compra_recibir(request, compra_id):
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import os
    from datetime import datetime
    from django.utils import timezone
    
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor").prefetch_related("detalles__producto"),
        id=compra_id
    )
    
    # Validar que esté aprobada
    if compra.estado != 'aprobado':
        messages.error(request, "Solo se pueden recibir compras aprobadas")
        return redirect("compra_ver", compra_id=compra.id)
    
    # Validar que no esté ya recibida
    if compra.entrada_almacen_generada:
        messages.error(request, "Esta compra ya fue recibida")
        return redirect("compra_ver", compra_id=compra.id)
    
    # ========== INICIALIZAR VARIABLE ANTES DEL IF ==========
    fecha_recepcion = timezone.now().date()
    
    if request.method == "POST":
        try:
            with transaction.atomic():
                # ==========================================
                # 0. VALIDAR QUE LAS CANTIDADES RECIBIDAS NO SUPEREN LO PEDIDO
                # ==========================================
                errores_cantidad = []
                
                for detalle in compra.detalles.all():
                    cantidad_recibida_str = request.POST.get(f'cantidad_recibida_{detalle.id}', '0')
                    try:
                        cantidad_recibida = Decimal(cantidad_recibida_str)
                    except:
                        cantidad_recibida = Decimal('0')
                    
                    if cantidad_recibida > detalle.cantidad:
                        errores_cantidad.append(
                            f"Cantidad recibida ({cantidad_recibida}) no puede ser mayor a la pedida ({detalle.cantidad})"
                        )
                
                if errores_cantidad:
                    for error in errores_cantidad:
                        messages.error(request, error)
                    return redirect("compra_recibir", compra_id=compra.id)
                
                # ==========================================
                # 1. GUARDAR FECHA DE RECEPCIÓN
                # ==========================================
                fecha_recepcion_str = request.POST.get('fecha_recepcion')
                if fecha_recepcion_str:
                    try:
                        compra.fecha_recepcion = datetime.strptime(fecha_recepcion_str, '%d/%m/%Y').date()
                    except:
                        compra.fecha_recepcion = timezone.now().date()
                else:
                    compra.fecha_recepcion = timezone.now().date()
                
                # ==========================================
                # 2. GUARDAR PDF DE FACTURA
                # ==========================================
                if request.FILES.get('factura_pdf'):
                    factura_pdf = request.FILES['factura_pdf']
                    if factura_pdf.content_type == 'application/pdf':
                        compra.factura_pdf = factura_pdf
                    else:
                        messages.error(request, "Solo se permiten archivos PDF")
                        return redirect("compra_recibir", compra_id=compra.id)
                
                # ==========================================
                # 3. PROCESAR PRODUCTOS RECIBIDOS Y ACTUALIZAR STOCK
                # ==========================================
                observaciones_generales = request.POST.get('observaciones_generales', '')
                compra.observaciones_recepcion = observaciones_generales
                
                monto_real_recibido = Decimal('0.00')
                
                for detalle in compra.detalles.all():
                    cantidad_recibida_str = request.POST.get(f'cantidad_recibida_{detalle.id}', '0')
                    observacion = request.POST.get(f'observacion_{detalle.id}', '')
                    
                    try:
                        cantidad_recibida = Decimal(cantidad_recibida_str)
                    except:
                        cantidad_recibida = detalle.cantidad

                    detalle.cantidad_recibida = cantidad_recibida
                    
                    # Guardar observación si existe
                    if observacion:
                        detalle.observacion = observacion
                    
                    detalle.save(update_fields=['cantidad_recibida', 'observacion'])
                    
                    # Si la cantidad recibida es diferente a la pedida, guardar observación
                    if cantidad_recibida != detalle.cantidad:
                        print(f"Producto {detalle.producto.nombre}: Pedido {detalle.cantidad}, Recibido {cantidad_recibida}")
                    
                    # ACTUALIZAR STOCK DEL PRODUCTO
                    if cantidad_recibida > 0:
                        producto = detalle.producto
                        producto.stock_actual += cantidad_recibida
                        producto.save(update_fields=['stock_actual'])
                        print(f"Stock actualizado: {producto.nombre} +{cantidad_recibida} = {producto.stock_actual}")
                        
                        # Calcular monto real recibido
                        monto_real_recibido += cantidad_recibida * detalle.producto.costo_unitario
                
                # ==========================================
                # 4. ACTUALIZAR ESTADO DE LA COMPRA
                # ==========================================
                compra.estado = 'recibido'
                compra.entrada_almacen_generada = True
                compra.save(update_fields=[
                    'estado', 
                    'entrada_almacen_generada',
                    'fecha_recepcion',
                    'factura_pdf',
                    'observaciones_recepcion'
                ])
                
                # ==========================================
                # 5. CREAR MOVIMIENTO FINANCIERO (EGRESO POR EL MONTO REAL)
                # ==========================================
                from finanza.views import crear_movimiento_compra
                if monto_real_recibido > 0:
                    crear_movimiento_compra(compra, request.user, monto_real_recibido)
                
                # ==========================================
                # 6. BITACORA
                # ==========================================
                BitacoraCompra.registrar(
                    compra,
                    "RECEPCIÓN",
                    f"Compra recibida el {compra.fecha_recepcion}. Monto real: {monto_real_recibido}. Observaciones: {observaciones_generales[:100]}",
                    request.user
                )
                
                messages.success(request, f"Compra #{compra.id} recibida. Monto: {monto_real_recibido}")
                messages.info(request, "Stock actualizado")
                return redirect("compra_ver", compra_id=compra.id)
                
        except Exception as e:
            messages.error(request, f"Error al recibir compra: {str(e)}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return redirect("compra_recibir", compra_id=compra.id)
    
    return render(request, "compras/compra_recibir.html", {
        "compra": compra,
        "fecha_recepcion": fecha_recepcion,
    })


# ==========================================================
# IMPRIMIR
# ==========================================================

@login_required
@permission_required("seguridad.imprimir_compras", raise_exception=True)
def compra_imprimir(request, compra_id):
    
    compra = get_object_or_404(
        Compra.objects.select_related(
            "proveedor",
        ).prefetch_related(
            "detalles__producto"
        ),
        id=compra_id
    )
    
    # Obtener configuración del taller usando get_config
    config = {
        "nombre_taller": get_config("nombre_taller", "Iam Car - Taller Automotriz"),
        "ruc_taller": get_config("ruc_taller", "—"),
        "direccion_taller": get_config("direccion_taller", "Asunción, Paraguay"),
        "telefono_taller": get_config("telefono_taller", "—"),
    }

    return render(
        request,
        "compras/compra_imprimir.html",
        {
            "compra": compra,
            "config": config,
        }
    )



@login_required
@permission_required("seguridad.recibir_compras", raise_exception=True)
def compra_cargar_factura(request, compra_id):
    from datetime import datetime
    
    compra = get_object_or_404(Compra, id=compra_id)
    
    if compra.estado != 'recibido':
        messages.error(request, "Solo se puede cargar factura para compras recibidas")
        return redirect("compra_ver", compra_id=compra.id)
    
    if request.method == "POST":
        if request.FILES.get('factura_pdf'):
            factura_pdf = request.FILES['factura_pdf']
            if factura_pdf.content_type == 'application/pdf':
                compra.factura_pdf = factura_pdf
            else:
                messages.error(request, "Solo se permiten archivos PDF")
                return redirect("compra_ver", compra_id=compra.id)
        
        # Fecha de recepción
        fecha_recepcion_str = request.POST.get('fecha_recepcion')
        if fecha_recepcion_str:
            try:
                compra.fecha_recepcion = datetime.strptime(fecha_recepcion_str, '%d/%m/%Y').date()
            except:
                pass
        
        compra.save(update_fields=['factura_pdf', 'fecha_recepcion'])
        
        BitacoraCompra.registrar(
            compra,
            "CARGA FACTURA",
            "Se cargó la factura/recibo",
            request.user
        )
        
        messages.success(request, "Factura / Recibo agregado ")
    
    return redirect("compra_ver", compra_id=compra.id)


# ==========================================================
# BÚSQUEDAS
# ==========================================================

@login_required
def buscar_proveedores_autocomplete(request):
    """Vista para autocompletar proveedores"""
    query = request.GET.get('q', '').strip()
    
    try:
        
        proveedores = Proveedor.objects.filter(is_active=True)
        
        if query:
            proveedores = proveedores.filter(
                Q(razon_social__icontains=query) |
                Q(ruc__icontains=query)
            )
        
        proveedores = proveedores.order_by('razon_social')[:20]
        
        data = [{
            'id': p.id,
            'text': f"{p.razon_social} - {p.ruc}",
            'ruc': p.ruc or '',
            'razon_social': p.razon_social or ''
        } for p in proveedores]
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        print(f"Error en buscar_proveedores_autocomplete: {e}")
        return JsonResponse([], safe=False)
    

@login_required
def buscar_insumos_compra(request):
    """Vista para autocompletar insumos para compras"""
    query = request.GET.get('q', '').strip()
    
    try:
        # SOLO insumos activos que se pueden comprar
        insumos = Insumo.objects.filter(is_active=True)
        
        # Aplicar filtro de búsqueda si hay query
        if query:
            insumos = insumos.filter(
                Q(nombre__icontains=query) |
                Q(id__icontains=query)
            )
        
        # Ordenar y limitar resultados (Siempre devolver algunos resultados)
        insumos = insumos.order_by('nombre')[:20]
        
        # Formatear respuesta
        insumos_data = []
        for insumo in insumos:
            insumos_data.append({
                'id': insumo.pk,
                'text': insumo.nombre,
                'nombre': insumo.nombre,
                'codigo': str(insumo.id),
                'costo_unitario': float(insumo.costo_unitario) if insumo.costo_unitario else 0,
                'stock_actual': float(insumo.stock_actual) if insumo.stock_actual else 0,
                'unidad': insumo.get_unidad_display() if hasattr(insumo, 'get_unidad_display') else insumo.unidad,
            })
        
        return JsonResponse(insumos_data, safe=False)
        
    except Exception as e:
        print(f"Error en buscar_insumos_compra: {e}")
        return JsonResponse([], safe=False)
    

# Agrega al inicio del archivo
from finanza.views import crear_movimiento_compra, ajustar_movimiento_compra

@login_required
@permission_required("seguridad.cambiar_estado_compras", raise_exception=True)
def compra_aprobar(request, compra_id):
    compra = get_object_or_404(Compra, id=compra_id)
    if compra.estado == "pendiente":
        compra.estado = "aprobado"
        compra.save(update_fields=["estado"])

        BitacoraCompra.registrar(
            compra,
            "APROBADA",
            "Orden aprobada",
            request.user
        )
        
        # ========== CREAR MOVIMIENTO FINANCIERO ==========
        if compra.total > 0:
            crear_movimiento_compra(compra, request.user)
        
        messages.success(request, f"Orden de compra #{compra.id} aprobada")

    else:
        messages.error(
            request,
            _("Solo se pueden aprobar compras pendientes")
        )
    return redirect("compra_cambiar_estados")