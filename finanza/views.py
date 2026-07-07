# pylint: disable=no-member
# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

import logging
from decimal import Decimal

from django.contrib import messages

logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from datetime import timedelta

from django.utils import timezone

from .forms import (
    CajaForm,
    MovimientoFinancieroForm,
    CobroForm,
    PagoProveedorForm,
    GastoForm,
    PagoGastoForm,
)

from .models import (
    Caja,
    MovimientoFinanciero,
    CuentaCobrar,
    CuentaPagar,
    Gasto,
)


# ==========================================================
# FUNCIONES AUXILIARES PARA MOVIMIENTOS FINANCIEROS
# ==========================================================
def crear_movimiento_factura(factura, usuario=None):
    """
    Crea o actualiza un movimiento financiero de ingreso cuando se emite una factura
    """
    try:
        caja = Caja.objects.filter(estado="abierta").first()
        if not caja:
            logger.warning("No hay caja abierta para registrar el movimiento")
            return None

        if factura.estado != 'ACTIVA':
            logger.warning("Factura %s no está activa", factura.numero_formateado)
            return None

        factura.refresh_from_db()

        if factura.total_general <= 0:
            logger.warning("Factura %s tiene total 0, no se crea movimiento", factura.numero_formateado)
            return None

        movimiento = MovimientoFinanciero.objects.filter(
            factura=factura,
            tipo="ingreso"
        ).first()

        if movimiento:
            movimiento.monto = factura.total_general
            movimiento.descripcion = f"Factura {factura.numero_formateado} - {factura.cliente_nombre or 'CONSUMIDOR FINAL'}"
            movimiento.save(update_fields=['monto', 'descripcion'])
            logger.info("Movimiento ACTUALIZADO para factura %s: %s", factura.numero_formateado, movimiento.monto)
            return movimiento
        else:
            movimiento = MovimientoFinanciero.objects.create(
                caja=caja,
                tipo="ingreso",
                origen="factura",
                descripcion=f"Factura {factura.numero_formateado} - {factura.cliente_nombre or 'CONSUMIDOR FINAL'}",
                monto=factura.total_general,
                fecha=timezone.now(),
                factura=factura,
                usuario=usuario
            )
            logger.info("Movimiento INGRESO creado para factura %s: %s", factura.numero_formateado, movimiento.monto)
            return movimiento
    except Exception as e:
        logger.exception("Error al crear movimiento para factura: %s", e)
        return None


def crear_movimiento_nota_credito(nota, usuario=None):
    """
    Crea el movimiento financiero cuando la nota de crédito cambia a APROBADA
    """
    try:
        if MovimientoFinanciero.objects.filter(
            factura=nota.factura,
            descripcion__icontains=nota.numero_formateado,
            tipo="egreso"
        ).exists():
            logger.warning("Ya existe movimiento para nota %s", nota.numero_formateado)
            return None

        caja = Caja.objects.filter(estado="abierta").first()
        if not caja:
            logger.warning("No hay caja abierta para registrar el movimiento")
            return None

        if nota.total_general <= 0:
            logger.warning("Nota %s tiene total 0, no se crea movimiento", nota.numero_formateado)
            return None

        tipo = "TOTAL" if nota.total_general >= nota.factura.total_general else "PARCIAL"

        movimiento = MovimientoFinanciero.objects.create(
            caja=caja,
            tipo="egreso",
            origen="factura",
            descripcion=f"Nota de Crédito {nota.numero_formateado} ({tipo}) - Factura {nota.factura.numero_formateado} - {nota.motivo[:50]}",
            monto=nota.total_general,
            fecha=timezone.now(),
            factura=nota.factura,
            usuario=usuario
        )
        logger.info("Movimiento EGRESO creado para nota de crédito %s: %s", nota.numero_formateado, movimiento.monto)
        return movimiento
    except Exception as e:
        logger.exception("Error al crear movimiento para nota de crédito: %s", e)
        return None


def anular_movimiento_factura(factura, usuario):
    """
    Anula el movimiento de ingreso de una factura (cuando se anula la factura)
    """
    try:
        movimiento_ingreso = MovimientoFinanciero.objects.filter(
            factura=factura,
            tipo="ingreso"
        ).first()

        if not movimiento_ingreso:
            logger.warning("No se encontró movimiento de ingreso para factura %s", factura.numero_formateado)
            return None

        if MovimientoFinanciero.objects.filter(
            factura=factura,
            tipo="egreso",
            descripcion__icontains="ANULACIÓN"
        ).exists():
            logger.warning("Ya existe movimiento de anulación para factura %s", factura.numero_formateado)
            return None

        caja = Caja.objects.filter(estado="abierta").first()
        if not caja:
            logger.warning("No hay caja abierta para anular el movimiento")
            return None

        movimiento_anulacion = MovimientoFinanciero.objects.create(
            caja=caja,
            tipo="egreso",
            origen="factura",
            descripcion=f"ANULACIÓN - Factura {factura.numero_formateado} - {factura.cliente_nombre or 'CONSUMIDOR FINAL'}",
            monto=movimiento_ingreso.monto,
            fecha=timezone.now(),
            factura=factura,
            usuario=usuario
        )
        logger.info("Movimiento de ANULACIÓN creado para factura %s: %s", factura.numero_formateado, movimiento_anulacion.monto)
        return movimiento_anulacion
    except Exception as e:
        logger.exception("Error al anular movimiento de factura: %s", e)
        return None


# ==========================================================
# DASHBOARD
# ==========================================================

@login_required
@permission_required(
 "seguridad.ver_finanzas",
  raise_exception=True
)
def dashboard_finanza(request):

    caja_abierta = Caja.objects.filter(
        estado="abierta"
    ).first()

    ingresos = (
        MovimientoFinanciero.objects.filter(
            tipo="ingreso"
        ).aggregate(
            total=Sum("monto")
        )["total"]
        or Decimal("0.00")
    )

    egresos = (
        MovimientoFinanciero.objects.filter(
            tipo="egreso"
        ).aggregate(
            total=Sum("monto")
        )["total"]
        or Decimal("0.00")
    )

    balance = ingresos - egresos

    return render(
        request,
        "finanza/dashboard_finanza.html",
        {
            "caja_abierta": caja_abierta,
            "ingresos": ingresos,
            "egresos": egresos,
            "balance": balance,
            "movimientos": MovimientoFinanciero.objects.select_related(
                "usuario",
            ).all()[:10],
            "cuentas_cobrar": CuentaCobrar.objects.filter(
                pagado=False
            ).count(),
            "cuentas_pagar": CuentaPagar.objects.filter(
                pagado=False
            ).count(),
        }
    )


# ==========================================================
# LISTA MOVIMIENTOS
# ==========================================================

@login_required
@permission_required(
    "seguridad.ver_finanzas",
    raise_exception=True
)
def movimiento_lista(request):

    movimientos = (
        MovimientoFinanciero.objects
        .select_related(
            "caja",
            "usuario",
            "factura",
            "compra",
        )
        .all()
    )

    q = request.GET.get("q")

    if q:
        movimientos = movimientos.filter(
            descripcion__icontains=q
        )

    tipo = request.GET.get("tipo")

    if tipo:
        movimientos = movimientos.filter(
            tipo=tipo
        )

    paginator = Paginator(
        movimientos,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "finanza/movimiento_lista.html",
        {
            "movimientos": page_obj,
        }
    )


# ==========================================================
# CREAR MOVIMIENTO
# ==========================================================

@login_required
@permission_required(
    "seguridad.gestionar_finanzas",
    raise_exception=True
)
def movimiento_crear(request):

    caja = Caja.objects.filter(
        estado="abierta"
    ).first()

    if not caja:

        messages.error(
            request,
            "No existe una caja abierta."
        )

        return redirect("dashboard_finanza")

    if request.method == "POST":

        form = MovimientoFinancieroForm(
            request.POST
        )

        if form.is_valid():

            movimiento = form.save(
                commit=False
            )

            movimiento.caja = caja
            movimiento.usuario = request.user
            movimiento.save()

            messages.success(
                request,
                "Movimiento registrado"
            )

            return redirect(
                "movimiento_lista"
            )

    else:

        form = MovimientoFinancieroForm()

    return render(
        request,
        "finanza/movimiento_crear.html",
        {
            "form": form,
        }
    )



# ==========================================================
# LISTA CAJAS
# ==========================================================

@login_required
@permission_required(
    "seguridad.ver_finanzas",
    raise_exception=True
)
def caja_lista(request):

    cajas = Caja.objects.select_related(
        "usuario_apertura",
        "usuario_cierre",
    ).all()

    paginator = Paginator(
        cajas,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "finanza/caja_lista.html",
        {
            "cajas": page_obj,
        }
    )


# ==========================================================
# APERTURA CAJA
# ==========================================================

@login_required
@permission_required(
    "seguridad.abrir_caja",
    raise_exception=True
)
def caja_apertura(request):

    caja_abierta = Caja.objects.filter(
        estado="abierta"
    ).exists()

    if caja_abierta:

        messages.error(
            request,
            "Ya existe una caja abierta"
        )

        return redirect(
            "caja_lista"
        )

    if request.method == "POST":

        form = CajaForm(
            request.POST
        )

        if form.is_valid():

            caja = form.save(
                commit=False
            )

            caja.usuario_apertura = request.user
            caja.saldo_actual = caja.monto_inicial
            caja.save()

            messages.success(
                request,
                "Apertura de caja"
            )

            return redirect(
                "caja_lista"
            )

    else:

        form = CajaForm()

    return render(
        request,
        "finanza/caja_apertura.html",
        {
            "form": form,
        }
    )


# ==========================================================
# CIERRE CAJA
# ==========================================================

@login_required
@permission_required(
    "seguridad.cerrar_caja",
    raise_exception=True
)
def caja_cierre(request, caja_id):

    caja = get_object_or_404(
        Caja,
        pk=caja_id
    )

    if caja.estado == "cerrada":

        messages.error(
            request,
            "La caja ya está cerrada"
        )

        return redirect(
            "caja_lista"
        )

    caja.total_ingresos_cierre = caja.total_ingresos
    caja.total_egresos_cierre = caja.total_egresos
    caja.saldo_cierre = caja.saldo_actual

    caja.estado = "cerrada"
    caja.fecha_cierre = timezone.now()
    caja.usuario_cierre = request.user

    caja.save(
       update_fields=[
        "total_ingresos_cierre",
        "total_egresos_cierre",
        "saldo_cierre",
        "estado",
        "fecha_cierre",
        "usuario_cierre",
        ]
    )

    messages.success(
        request,
        "Cierre de caja"
    )

    return redirect(
        "caja_lista"
    )


# ==========================================================
# CUENTAS POR COBRAR
# ==========================================================

@login_required
@permission_required(
    "seguridad.ver_finanzas",
    raise_exception=True
)
def cuentas_cobrar(request):

    cuentas = (
        CuentaCobrar.objects
        .select_related(
            "cliente",
            "factura",
        )
        .all()
    )

    paginator = Paginator(
        cuentas,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "finanza/cuentas_cobrar.html",
        {
            "cuentas": page_obj,
        }
    )


# ==========================================================
# CUENTAS POR PAGAR
# ==========================================================

@login_required
@permission_required(
    "seguridad.ver_finanzas",
    raise_exception=True
)
def cuentas_pagar(request):

    cuentas = (
        CuentaPagar.objects
        .select_related(
            "proveedor",
            "compra",
        )
        .all()
    )

    paginator = Paginator(
        cuentas,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "finanza/cuentas_pagar.html",
        {
            "cuentas": page_obj,
        }
    )


# ==========================================================
# REGISTRAR COBRO
# ==========================================================

@login_required
@permission_required(
    "seguridad.gestionar_finanzas",
    raise_exception=True
)
def cobro_crear(request, cuenta_id):

    cuenta = get_object_or_404(
        CuentaCobrar,
        pk=cuenta_id
    )

    if request.method == "POST":

        form = CobroForm(request.POST)

        if form.is_valid():

            monto = form.cleaned_data.get("monto")

            if monto and monto > cuenta.saldo_pendiente:

                form.add_error(
                    "monto",
                    f"El monto no puede superar el saldo pendiente (₲ {cuenta.saldo_pendiente:.2f})."
                )

            else:

                cobro = form.save(
                    commit=False
                )

                cobro.cuenta = cuenta
                cobro.usuario = request.user
                cobro.save()

                messages.success(
                    request,
                    "Cobro registrado"
                )

                return redirect(
                    "cuentas_cobrar"
                )

    else:

        form = CobroForm()

    return render(
        request,
        "finanza/cobro_crear.html",
        {
            "form": form,
            "cuenta": cuenta,
        }
    )


# ==========================================================
# REGISTRAR PAGO PROVEEDOR
# ==========================================================

@login_required
@permission_required(
    "seguridad.gestionar_finanzas",
    raise_exception=True
)
def pago_proveedor_crear(request, cuenta_id):

    cuenta = get_object_or_404(
        CuentaPagar,
        pk=cuenta_id
    )

    if request.method == "POST":

        form = PagoProveedorForm(
            request.POST
        )

        if form.is_valid():

            monto = form.cleaned_data.get("monto")

            if monto and monto > cuenta.saldo_pendiente:

                form.add_error(
                    "monto",
                    f"El monto no puede superar el saldo pendiente (₲ {cuenta.saldo_pendiente:.2f})."
                )

            else:

                pago = form.save(
                    commit=False
                )

                pago.cuenta = cuenta
                pago.usuario = request.user
                pago.save()

                messages.success(
                    request,
                    "Pago registrado"
                )

                return redirect(
                    "cuentas_pagar"
                )

    else:

        form = PagoProveedorForm()

    return render(
        request,
        "finanza/pago_proveedor_crear.html",
        {
            "form": form,
            "cuenta": cuenta,
        }
    )


def crear_movimiento_compra(compra, usuario=None, monto_real=None):
    """
    Crea o actualiza un movimiento financiero de egreso cuando se recibe una compra
    """
    try:
        caja = Caja.objects.filter(estado="abierta").first()
        if not caja:
            logger.warning("No hay caja abierta para registrar el movimiento")
            return None

        if monto_real is None:
            compra.refresh_from_db()
            monto_real = compra.total

        if monto_real <= 0:
            logger.warning("Compra %s tiene monto 0, no se crea movimiento", compra.id)
            return None

        movimiento = MovimientoFinanciero.objects.filter(
            compra=compra,
            tipo="egreso"
        ).first()

        if movimiento:
            movimiento.monto = monto_real
            movimiento.descripcion = f"Compra #{compra.id} - {compra.proveedor.razon_social if compra.proveedor else 'Sin proveedor'}"
            movimiento.save(update_fields=['monto', 'descripcion'])
            logger.info("Movimiento ACTUALIZADO para compra %s: %s", compra.id, movimiento.monto)
            return movimiento
        else:
            movimiento = MovimientoFinanciero.objects.create(
                caja=caja,
                tipo="egreso",
                origen="compra",
                descripcion=f"Compra #{compra.id} - {compra.proveedor.razon_social if compra.proveedor else 'Sin proveedor'}",
                monto=monto_real,
                fecha=timezone.now(),
                compra=compra,
                usuario=usuario
            )
            logger.info("Movimiento EGRESO creado para compra %s: %s", compra.id, movimiento.monto)
            return movimiento
    except Exception as e:
        logger.exception("Error al crear movimiento para compra: %s", e)
        return None


def ajustar_movimiento_compra(compra, usuario, monto_real):
    """
    Ajusta el movimiento de una compra cuando la recepción es parcial
    """
    try:
        caja = Caja.objects.filter(estado="abierta").first()
        if not caja:
            return None

        movimiento_original = MovimientoFinanciero.objects.filter(
            compra=compra,
            tipo="egreso"
        ).first()

        if not movimiento_original:
            return None

        diferencia = movimiento_original.monto - monto_real

        if diferencia <= 0:
            return None

        movimiento_ajuste = MovimientoFinanciero.objects.create(
            caja=caja,
            tipo="ingreso",
            origen="compra",
            descripcion=f"AJUSTE - Compra #{compra.id} (Recepción parcial - Diferencia: {diferencia})",
            monto=diferencia,
            fecha=timezone.now(),
            compra=compra,
            usuario=usuario
        )
        logger.info("Movimiento de AJUSTE creado para compra %s: %s", compra.id, diferencia)
        return movimiento_ajuste
    except Exception as e:
        logger.exception("Error al ajustar movimiento de compra: %s", e)
        return None


# ==========================================================
# GASTOS
# ==========================================================
@login_required
@permission_required('finanza.ver_finanzas', raise_exception=True)
def gasto_lista(request):
    gastos = Gasto.objects.all().order_by('-fecha', '-created_at')

    sucursal_id = request.session.get('sucursal_id')
    if sucursal_id:
        gastos = gastos.filter(sucursal_id=sucursal_id)

    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    if tipo:
        gastos = gastos.filter(tipo=tipo)
    if estado:
        gastos = gastos.filter(estado=estado)
    if fecha_desde:
        gastos = gastos.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        gastos = gastos.filter(fecha__lte=fecha_hasta)

    # Paginación
    paginator = Paginator(gastos, 20)
    page_number = request.GET.get('page')
    gastos = paginator.get_page(page_number)

    # Totales
    total_pendiente = sum(g.monto for g in gastos if g.estado in ('pendiente', 'vencido'))
    total_pagado = sum(g.monto for g in gastos if g.estado == 'pagado')

    context = {
        'gastos': gastos,
        'total_pendiente': total_pendiente,
        'total_pagado': total_pagado,
        'TIPO_CHOICES': Gasto.TIPO_CHOICES,
        'ESTADO_CHOICES': Gasto.ESTADO_CHOICES,
        'filtros': {
            'tipo': tipo,
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        },
    }
    return render(request, 'finanza/gasto_lista.html', context)


@login_required
@permission_required('finanza.gestionar_finanzas', raise_exception=True)
def gasto_crear(request):
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.usuario = request.user
            gasto.sucursal_id = request.session.get('sucursal_id')
            gasto.save()
            messages.success(request, 'Gasto registrado correctamente')
            return redirect('gasto_lista')
    else:
        form = GastoForm()

    return render(request, 'finanza/gasto_form.html', {'form': form, 'accion': 'Crear'})


@login_required
@permission_required('finanza.ver_finanzas', raise_exception=True)
def gasto_detalle(request, gasto_id):
    gasto = get_object_or_404(Gasto, pk=gasto_id)
    pagos = gasto.pagos.all()
    return render(request, 'finanza/gasto_detalle.html', {
        'gasto': gasto,
        'pagos': pagos,
    })


@login_required
@permission_required('finanza.gestionar_finanzas', raise_exception=True)
def gasto_pagar(request, gasto_id):
    gasto = get_object_or_404(Gasto, pk=gasto_id)

    if gasto.estado == 'pagado':
        messages.warning(request, 'Este gasto ya está pagado')
        return redirect('gasto_detalle', gasto_id=gasto.id)

    cajas_abiertas = Caja.objects.filter(estado='abierta')
    sucursal_id = request.session.get('sucursal_id')
    if sucursal_id:
        cajas_abiertas = cajas_abiertas.filter(sucursal_id=sucursal_id)

    if request.method == 'POST':
        form = PagoGastoForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.gasto = gasto
            pago.usuario = request.user
            pago.sucursal_id = sucursal_id
            pago.save()
            messages.success(request, f'Pago de {pago.monto} registrado para {gasto.concepto}')
            return redirect('gasto_detalle', gasto_id=gasto.id)
    else:
        form = PagoGastoForm()
        form.fields['caja'].queryset = cajas_abiertas

    return render(request, 'finanza/gasto_pagar.html', {
        'form': form,
        'gasto': gasto,
        'cajas_abiertas': cajas_abiertas,
    })


# ==========================================================
# REPORTES FINANCIEROS
# ==========================================================
@login_required
@permission_required('finanza.ver_reportes_financieros', raise_exception=True)
def reportes_financieros(request):
    sucursal_id = request.session.get('sucursal_id')

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    # Base filters
    ing_filter = Q(tipo='ingreso', fecha__date__gte=inicio_mes, fecha__date__lte=hoy)
    egr_filter = Q(tipo='egreso', fecha__date__gte=inicio_mes, fecha__date__lte=hoy)

    if sucursal_id:
        ing_filter &= Q(sucursal_id=sucursal_id)
        egr_filter &= Q(sucursal_id=sucursal_id)

    ingresos_mes = MovimientoFinanciero.objects.filter(ing_filter).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    egresos_mes = MovimientoFinanciero.objects.filter(egr_filter).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    # Gastos por tipo (mes actual)
    gasto_filter = Q(fecha__gte=inicio_mes, fecha__lte=hoy, activo=True) & ~Q(estado='anulado')
    if sucursal_id:
        gasto_filter &= Q(sucursal_id=sucursal_id)
    gastos_por_tipo = Gasto.objects.filter(gasto_filter).values('tipo').annotate(total=Sum('monto')).order_by('-total')

    for item in gastos_por_tipo:
        item['tipo_display'] = dict(Gasto.TIPO_CHOES).get(item['tipo'], item['tipo'])

    # Cuentas pendientes
    cc_filter = Q(pagado=False)
    cp_filter = Q(pagado=False)
    if sucursal_id:
        cc_filter &= Q(sucursal_id=sucursal_id)
        cp_filter &= Q(sucursal_id=sucursal_id)

    cuentas_cobrar_pend = CuentaCobrar.objects.filter(cc_filter).count()
    cuentas_pagar_pend = CuentaPagar.objects.filter(cp_filter).count()
    total_por_cobrar = CuentaCobrar.objects.filter(cc_filter).aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')
    total_por_pagar = CuentaPagar.objects.filter(cp_filter).aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')

    # Movimientos recientes
    mov_filter = Q()
    if sucursal_id:
        mov_filter = Q(sucursal_id=sucursal_id)
    movimientos_recientes = MovimientoFinanciero.objects.filter(mov_filter).order_by('-fecha')[:10]

    context = {
        'ingresos_mes': ingresos_mes,
        'egresos_mes': egresos_mes,
        'balance_mes': ingresos_mes - egresos_mes,
        'gastos_por_tipo': gastos_por_tipo,
        'cuentas_cobrar_pend': cuentas_cobrar_pend,
        'cuentas_pagar_pend': cuentas_pagar_pend,
        'total_por_cobrar': total_por_cobrar,
        'total_por_pagar': total_por_pagar,
        'movimientos_recientes': movimientos_recientes,
    }
    return render(request, 'finanza/reportes.html', context)


@login_required
@permission_required('finanza.ver_reportes_financieros', raise_exception=True)
def reporte_balance(request):
    sucursal_id = request.session.get('sucursal_id')

    fecha_desde = request.GET.get('fecha_desde', (timezone.localdate() - timedelta(days=30)).isoformat())
    fecha_hasta = request.GET.get('fecha_hasta', timezone.localdate().isoformat())

    mov_filter = Q(fecha__date__gte=fecha_desde, fecha__date__lte=fecha_hasta)
    if sucursal_id:
        mov_filter &= Q(sucursal_id=sucursal_id)

    movimientos = MovimientoFinanciero.objects.filter(mov_filter).order_by('-fecha')

    ingresos = movimientos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    egresos = movimientos.filter(tipo='egreso').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    # Por medio de pago
    ingresos_por_medio = movimientos.filter(tipo='ingreso').values('medio_pago').annotate(total=Sum('monto')).order_by('-total')
    egresos_por_medio = movimientos.filter(tipo='egreso').values('medio_pago').annotate(total=Sum('monto')).order_by('-total')

    context = {
        'movimientos': movimientos,
        'ingresos': ingresos,
        'egresos': egresos,
        'balance': ingresos - egresos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'ingresos_por_medio': ingresos_por_medio,
        'egresos_por_medio': egresos_por_medio,
    }
    return render(request, 'finanza/reporte_balance.html', context)


# ==========================================================
# CIERRE DE CAJA IMPRIMIBLE
# ==========================================================
@login_required
@permission_required('finanza.ver_finanzas', raise_exception=True)
def caja_imprimir(request, caja_id):
    caja = get_object_or_404(Caja, pk=caja_id)
    ingresos = caja.movimientos.filter(tipo='ingreso')
    egresos = caja.movimientos.filter(tipo='egreso')

    total_ingresos = ingresos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    total_egresos = egresos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    context = {
        'caja': caja,
        'ingresos': ingresos,
        'egresos': egresos,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
    }
    return render(request, 'finanza/caja_imprimir.html', context)


