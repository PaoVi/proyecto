from decimal import Decimal, ROUND_UP
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError


class ControlCargaService:
    """
    Servicio para controlar la asignación y liberación de horas de empleados.
    """
    
    @classmethod
    def calcular_horas_empleado(cls, empleado):
        """Calcula las horas TOTALES asignadas a un empleado en órdenes ACTIVAS."""
        from .models import AsignacionOrden  # ✅ Importar dentro del método
        
        estados_activos = ['en_proceso']
        
        asignaciones = AsignacionOrden.objects.filter(
            empleado=empleado,
            orden__estado__in=estados_activos,
            estado__in=['asignado', 'en_ejecucion']
        ).select_related('servicio__servicio', 'registro_tiempo_real')
        
        total_minutos = 0
        for asignacion in asignaciones:
            if not asignacion.servicio:
                continue
            
            if asignacion.registro_tiempo_real:
                if asignacion.registro_tiempo_real.estado == 'en_curso':
                    tiempo_minutos = asignacion.servicio.servicio.tiempo_min_estimado or 0
                    total_minutos += tiempo_minutos
            else:
                tiempo_minutos = asignacion.servicio.servicio.tiempo_min_estimado or 0
                total_minutos += tiempo_minutos
        
        horas_totales = total_minutos // 60
        minutos_totales = total_minutos % 60
        horas_formateadas = f"{horas_totales:02d}:{minutos_totales:02d}"
        
        return {
            'minutos': total_minutos,
            'horas': total_minutos / 60,
            'horas_formateadas': horas_formateadas
        }
    
    @classmethod
    def verificar_estado_carga(cls, empleado):
        """Verifica el estado de carga actual de un empleado"""
        horas = empleado.horas_activas()
        limite = empleado.limite_horas_diarias or 8
        
        total_minutos = int(horas * 60)
        horas_enteras = total_minutos // 60
        minutos_restantes = total_minutos % 60
        horas_formateadas = f"{horas_enteras:02d}:{minutos_restantes:02d}"
        
        limite_minutos = limite * 60
        minutos_restantes_totales = max(0, limite_minutos - total_minutos)
        restante_horas = int(minutos_restantes_totales // 60)
        restante_minutos = int(minutos_restantes_totales % 60)
        restante_formateado = f"{restante_horas:02d}:{restante_minutos:02d}"
        
        porcentaje = (horas / limite) * 100 if limite > 0 else 0
        
        if horas >= limite:
            nivel = 'peligro'
            mensaje = f'¡SOBRECARGADO! {horas_formateadas} / {limite}h'
            sobrecargado = True
        elif horas >= limite * 0.8:
            nivel = 'advertencia'
            mensaje = f'Cerca del límite: {horas_formateadas} / {limite}h'
            sobrecargado = False
        elif horas >= limite * 0.5:
            nivel = 'info'
            mensaje = f'Carga media: {horas_formateadas} / {limite}h'
            sobrecargado = False
        else:
            nivel = 'normal'
            mensaje = f'Disponible: {horas_formateadas} / {limite}h'
            sobrecargado = False
        
        return {
            'total_minutos': total_minutos,
            'total_horas': horas,
            'total_horas_formateadas': horas_formateadas,
            'limite_horas': limite,
            'limite_minutos': limite_minutos,
            'porcentaje': porcentaje,
            'minutos_restantes': minutos_restantes_totales,
            'minutos_restantes_formateados': restante_formateado,
            'nivel': nivel,
            'nivel_alerta': nivel,
            'mensaje': mensaje,
            'sobrecargado': sobrecargado
        }
    
    @staticmethod
    def minutos_a_hhmm(minutos):
        if minutos is None:
            return "00:00"
        try:
            minutos = int(float(minutos))
            horas = minutos // 60
            mins = minutos % 60
            return f"{horas:02d}:{mins:02d}"
        except (ValueError, TypeError):
            return "00:00"


class ComisionService:
    """
    Servicio para manejar el cálculo y asignación de comisiones a empleados.
    La comisión se calcula sobre el PRECIO BASE del servicio (mano_obra + costo_insumos)
    """

    @staticmethod
    def redondear_arriba(valor):
        """Redondea un Decimal hacia arriba sin decimales"""
        if valor is None:
            return Decimal('0')
        return valor.quantize(Decimal('1'), rounding=ROUND_UP)
    
    @classmethod
    def procesar_comisiones_orden(cls, orden):
        """
        Procesa todas las comisiones de una orden FACTURADA.
        Suma las comisiones al campo comision_por_cobrar del empleado.
        """
        from .models import AsignacionOrden  # ✅ Importar dentro del método
        
        # VALIDAR QUE LA ORDEN ESTÉ FACTURADA
        if orden.estado != 'facturado':
            print(f"DEBUG: Orden #{orden.id} no está facturada (estado: {orden.estado}), no se procesan comisiones")
            return False
        
        print(f"DEBUG: Procesando comisiones para orden #{orden.id} (FACTURADA)")
        
        with transaction.atomic():
            asignaciones = AsignacionOrden.objects.filter(
                orden=orden,
                estado__in=['asignado', 'en_ejecucion', 'liberado']
            ).select_related('empleado', 'servicio__servicio')
            
            comisiones_procesadas = 0
            
            for asignacion in asignaciones:
                if cls._procesar_comision_asignacion(asignacion):
                    comisiones_procesadas += 1
            
            print(f"DEBUG: Se procesaron {comisiones_procesadas} comisiones para orden #{orden.id}")
            return comisiones_procesadas > 0
    
    @classmethod
    def _procesar_comision_asignacion(cls, asignacion):
        """
        Calcula y asigna la comisión para una asignación específica.
        Si hay múltiples empleados en un servicio, la comisión se divide equitativamente.
        """
        from .models import AsignacionOrden 
        if not asignacion.servicio:
            return False
        
        servicio_orden = asignacion.servicio
        servicio = servicio_orden.servicio
        empleado = asignacion.empleado
        
        porcentaje = servicio.comision_porcentaje or Decimal('0')
        
        if porcentaje <= 0:
            print(f"DEBUG: Servicio {servicio.nombre} tiene porcentaje 0%, no hay comisión")
            return False
        
        # Calcular comisión TOTAL del servicio
        precio_base_servicio = servicio.precio_base
        cantidad = servicio_orden.cantidad
        subtotal_base = precio_base_servicio * cantidad
        comision_servicio = (subtotal_base * porcentaje) / Decimal('100')
        
        # CONTAR cuántos empleados están asignados a ESTE servicio
        total_empleados_servicio = AsignacionOrden.objects.filter(
            orden=asignacion.orden,
            servicio=servicio_orden
        ).count()
        
        # Dividir la comisión equitativamente entre todos los empleados del servicio
        if total_empleados_servicio > 1:
            comision_empleado = comision_servicio / Decimal(str(total_empleados_servicio))
        else:
            comision_empleado = comision_servicio
        
        comision_empleado = cls.redondear_arriba(comision_empleado)
        
        if comision_empleado > 0:
            print(f"DEBUG: {empleado.nombre} - Servicio: {servicio.nombre} - "
                f"Comisión servicio: {comision_servicio:.0f} Gs. / {total_empleados_servicio} empleados = {comision_empleado:.0f} Gs. ({porcentaje}%)")
            
            # Sumar a comision_por_cobrar
            empleado.comision_por_cobrar += comision_empleado
            empleado.save(update_fields=['comision_por_cobrar'])
            
            from .models import BitacoraOrden
            BitacoraOrden.registrar(
                asignacion.orden,
                "Comisión asignada",
                f"Empleado: {empleado.nombre}, Servicio: {servicio.nombre}, "
                f"Subtotal: {subtotal_base:,.0f} Gs., Comisión total servicio: {comision_servicio:,.0f} Gs., "
                f"Empleados en servicio: {total_empleados_servicio}, "
                f"Comisión para {empleado.nombre}: {comision_empleado:,.0f} Gs. ({porcentaje}%)"
            )
            return True
        
        return False

    @classmethod
    def calcular_comision_empleado(cls, orden, empleado):
        """
        Calcula la comisión de un empleado específico para una orden.
        Si hay múltiples empleados en un servicio, la comisión se divide equitativamente.
        """
        from .models import AsignacionOrden
        
        # Solo calcular si la orden está en estado que muestra comisión
        if orden.estado in ['cancelado']:
            return Decimal('0')
        
        comision_total = Decimal('0')
        
        # Obtener TODAS las asignaciones de este empleado en esta orden
        asignaciones_empleado = AsignacionOrden.objects.filter(
            orden=orden,
            empleado=empleado,
            servicio__isnull=False
        ).select_related('servicio__servicio')
        
        for asignacion_emp in asignaciones_empleado:
            servicio_orden = asignacion_emp.servicio
            
            if not servicio_orden or not servicio_orden.servicio.comision_porcentaje:
                continue
            
            porcentaje = servicio_orden.servicio.comision_porcentaje
            
            if porcentaje <= 0:
                continue
            
            # Calcular comisión total del servicio
            subtotal = servicio_orden.subtotal
            comision_servicio = (subtotal * porcentaje) / Decimal('100')
            
            # CONTAR cuántos empleados están asignados a ESTE servicio
            total_empleados_servicio = AsignacionOrden.objects.filter(
                orden=orden,
                servicio=servicio_orden
            ).count()
            
            # Si hay más de un empleado, dividir la comisión equitativamente
            if total_empleados_servicio > 1:
                comision_empleado = comision_servicio / Decimal(str(total_empleados_servicio))
            else:
                comision_empleado = comision_servicio
            
            comision_total += cls.redondear_arriba(comision_empleado)
        
        return comision_total
  
    @classmethod
    def procesar_finalizacion_servicio(cls, orden_servicio_id, empleado_id=None, usuario=None):
        """Procesa la finalización de un servicio específico por parte de un empleado."""
        from .models import OrdenServicio, AsignacionOrden, RegistroTiempoReal 
        from django.db import transaction as db_transaction
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            orden_servicio = OrdenServicio.objects.select_related('orden', 'servicio').get(
                id=orden_servicio_id
            )
            
            # Si ya se descontaron los insumos, salir
            if orden_servicio.insumos_descontados:
                return True, "Los insumos ya fueron descontados anteriormente"
            
            if orden_servicio.orden.estado != 'en_proceso':
                raise ValidationError("Solo se pueden finalizar servicios en órdenes 'En Proceso'")
            
            with db_transaction.atomic():
                orden_servicio = OrdenServicio.objects.select_for_update().get(id=orden_servicio_id)
                
                logger.info(f"=== PROCESANDO FINALIZACIÓN Servicio {orden_servicio.id} - Empleado {empleado_id} ===")
                
                # Buscar la asignación de ESTE empleado específico
                asignacion = AsignacionOrden.objects.filter(
                    orden=orden_servicio.orden,
                    servicio=orden_servicio,
                    empleado_id=empleado_id
                ).first()
                
                if not asignacion:
                    return False, "Este empleado no está asignado a este servicio"
                
                # Finalizar registro de tiempo de ESTE empleado
                registro_real = RegistroTiempoReal.objects.filter(
                    servicio_orden=orden_servicio,
                    empleado_id=empleado_id,
                    estado='en_curso'
                ).first()
                
                if registro_real:
                    registro_real.finalizar_trabajo()
                    logger.info(f"Registro de tiempo finalizado para empleado {empleado_id}")
                
                # Liberar SOLO la asignación de ESTE empleado
                asignacion.estado = 'liberado'
                asignacion.fecha_liberacion = timezone.now()
                asignacion.save(update_fields=['estado', 'fecha_liberacion'])
                
                # Verificar cuántos empleados aún están pendientes para este servicio
                asignaciones_pendientes = AsignacionOrden.objects.filter(
                    orden=orden_servicio.orden,
                    servicio=orden_servicio,
                    estado__in=['asignado', 'en_ejecucion']
                ).count()
                
                logger.info(f"Empleados pendientes para este servicio: {asignaciones_pendientes}")
                
                mensaje = ""
                
                # Si es el último empleado, marcar el servicio como completado y descontar insumos
                if asignaciones_pendientes == 0 and not orden_servicio.empleado_finalizado:
                    logger.info(f"=== ÚLTIMO EMPLEADO - Completando servicio y descontando insumos ===")
                    
                    from .services import StockService  
                    success, message = StockService.descontar_insumos_servicio(orden_servicio, usuario=usuario)
                    
                    if not success:
                        return False, f"Error al descontar insumos: {message}"
                    
                    # Marcar servicio como finalizado
                    orden_servicio.empleado_finalizado = True
                    orden_servicio.fecha_finalizacion_empleado = timezone.now()
                    orden_servicio.save(update_fields=['empleado_finalizado', 'fecha_finalizacion_empleado'])
                    
                    mensaje = f"Servicio '{orden_servicio.servicio.nombre}' completado. {message}"
                    logger.info(f"SERVICIO COMPLETADO - Descuento realizado")
                else:
                    mensaje = f"Finalizaste tu parte. Faltan {asignaciones_pendientes} empleado(s) para completar el servicio."
                    logger.info(f"NO ES EL ÚLTIMO EMPLEADO - Sin descuento")
            
            # Verificar si la orden se completa (esto NO descuenta insumos)
            orden_completada = cls._verificar_y_completar_orden(orden_servicio.orden)
            
            if orden_completada:
                mensaje += " Y la OT ha sido completada automáticamente"
            
            return True, mensaje
            
        except OrdenServicio.DoesNotExist:
            return False, "Servicio no encontrado"
        except Exception as e:
            logger.error(f"Error en procesar_finalizacion_servicio: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, str(e)

    @classmethod
    def _verificar_y_completar_orden(cls, orden):
        """SOLO cambia el estado de la orden. NO descuenta insumos."""
        from .models import BitacoraOrden 
        
        servicios = orden.ordenservicio_set.all()
        
        if not servicios.exists():
            return False
        
        todos_finalizados = all(s.empleado_finalizado for s in servicios)
        
        if todos_finalizados and orden.estado == 'en_proceso':
            orden.estado = 'completado'
            orden.fecha_fin = timezone.now()
            orden.save(update_fields=['estado', 'fecha_fin'])
            
            # ⚠️ NO procesar comisiones aquí - se procesan al facturar
            # ComisionService.procesar_comisiones_orden(orden)  ← ELIMINAR
            
            BitacoraOrden.registrar(
                orden,
                "Completado automático",
                "Todos los servicios fueron marcados como finalizados por empleados"
            )
            
            return True
        
        return False


class StockService:
    """
    Servicio para manejar el descuento de insumos del stock cuando se finaliza un servicio.
    """
    
    @classmethod
    def verificar_stock_servicio(cls, servicio_orden):
        """Verifica si hay stock suficiente para todos los insumos de un servicio."""
        from decimal import Decimal, ROUND_HALF_UP
        
        if not servicio_orden or not servicio_orden.pk:
            return []
        
        servicio = servicio_orden.servicio
        cantidad_servicio = servicio_orden.cantidad
        
        insumos_servicio = servicio.servicioinsumo_set.select_related('insumo').all()
        
        if not insumos_servicio.exists():
            return []
        
        insumos_faltantes = []
        
        for servicio_insumo in insumos_servicio:
            insumo = servicio_insumo.insumo
            
            # EXCEPCIÓN: No verificar herramientas
            if insumo.grupo == 'herramienta':
                continue
            
            # Calcular cantidad necesaria y redondear a 2 decimales
            cantidad_necesaria = servicio_insumo.cantidad * cantidad_servicio
            cantidad_necesaria = cantidad_necesaria.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if cantidad_necesaria > insumo.stock_actual:
                insumos_faltantes.append({
                    'nombre': insumo.nombre,
                    'necesario': float(cantidad_necesaria),
                    'disponible': float(insumo.stock_actual),
                    'faltante': float(cantidad_necesaria - insumo.stock_actual),
                    'unidad': insumo.get_unidad_display(),
                    'grupo': insumo.grupo
                })
        
        return insumos_faltantes

    @classmethod
    def descontar_insumos_servicio(cls, servicio_orden, usuario=None):
        from insumo.models import MovimientoStock  
        from decimal import Decimal, ROUND_HALF_UP

        if not servicio_orden or not servicio_orden.pk:
            return False, "Servicio no válido"
        
        # ===== VERIFICACIÓN POR FLAG: Si ya se descontaron, salir =====
        if servicio_orden.insumos_descontados:
            return True, "Los insumos ya fueron descontados anteriormente"
        
        # ===== VERIFICACIÓN POR MOVIMIENTO: Como respaldo =====
        if MovimientoStock.objects.filter(
            observaciones__icontains=f"OT #{servicio_orden.orden.id} - {servicio_orden.servicio.nombre}",
            motivo='venta'
        ).exists():
            servicio_orden.insumos_descontados = True
            servicio_orden.save(update_fields=['insumos_descontados'])
            return True, "Los insumos ya fueron descontados anteriormente"
        
        servicio = servicio_orden.servicio
        cantidad_servicio = servicio_orden.cantidad
        
        insumos_servicio = servicio.servicioinsumo_set.select_related('insumo').all()
        
        if not insumos_servicio.exists():
            servicio_orden.insumos_descontados = True
            servicio_orden.save(update_fields=['insumos_descontados'])
            return True, "El servicio no tiene insumos asociados"
        
        insumos_descontados = []
        errores = []
        
        for servicio_insumo in insumos_servicio:
            insumo = servicio_insumo.insumo
            
            if insumo.grupo == 'herramienta':
                continue
            
            cantidad_necesaria = servicio_insumo.cantidad * cantidad_servicio
            cantidad_necesaria = cantidad_necesaria.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if cantidad_necesaria > insumo.stock_actual:
                errores.append(
                    f"{insumo.nombre}: necesita {cantidad_necesaria} {insumo.get_unidad_display()}, "
                    f"stock disponible: {insumo.stock_actual}"
                )
                continue
            
            subinsumos_activos = insumo.subinsumos.filter(is_active=True, stock_actual__gt=0)
            
            if subinsumos_activos.exists():
                cantidad_restante = cantidad_necesaria
                for subinsumo in subinsumos_activos.order_by('numero'):
                    if cantidad_restante <= 0:
                        break
                    
                    if subinsumo.stock_actual <= cantidad_restante:
                        cantidad_restante -= subinsumo.stock_actual
                        subinsumo.is_active = False
                        subinsumo.stock_actual = 0
                        subinsumo.save()
                    else:
                        subinsumo.stock_actual -= cantidad_restante
                        subinsumo.stock_actual = subinsumo.stock_actual.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        cantidad_restante = 0
                        subinsumo.save()
                
                MovimientoStock.objects.create(
                    insumo=insumo,
                    tipo='salida',
                    cantidad=cantidad_necesaria,
                    motivo='venta',
                    observaciones=f"Consumo por servicio: {servicio.nombre} (OT #{servicio_orden.orden.id}) - Consumidos desde subinsumos",
                    usuario=usuario
                )
                
                insumo.stock_actual -= cantidad_necesaria
                insumo.stock_actual = insumo.stock_actual.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                insumo.save(update_fields=['stock_actual'])
                
            else:
                insumo.stock_actual -= cantidad_necesaria
                insumo.stock_actual = insumo.stock_actual.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                insumo.save(update_fields=['stock_actual'])
                
                MovimientoStock.objects.create(
                    insumo=insumo,
                    tipo='salida',
                    cantidad=cantidad_necesaria,
                    motivo='venta',
                    observaciones=f"Consumo por servicio: {servicio.nombre} (OT #{servicio_orden.orden.id})",
                    usuario=usuario
                )
            
            insumos_descontados.append({
                'nombre': insumo.nombre,
                'cantidad': float(cantidad_necesaria),
                'unidad': insumo.get_unidad_display()
            })
        
        if errores:
            return False, f"No se pudo descontar: {'; '.join(errores)}"
        
        servicio_orden.insumos_descontados = True
        servicio_orden.save(update_fields=['insumos_descontados'])
        
        if insumos_descontados:
            return True, f"Insumos descontados: {len(insumos_descontados)} items"
        
        return True, "No hay insumos para descontar (solo herramientas o sin insumos)"


class TiempoRealService:
    """
    Servicio para manejar el registro de tiempo REAL trabajado por empleados.
    """

    @classmethod
    def obtener_servicio_en_curso(cls, orden_trabajo):
        """Obtiene el servicio que actualmente tiene trabajo en curso."""
        from .models import RegistroTiempoReal  # ✅ Importar dentro
        
        registro = RegistroTiempoReal.objects.filter(
            orden_trabajo=orden_trabajo,
            estado='en_curso'
        ).select_related('servicio_orden').first()
        
        return registro.servicio_orden if registro else None
    
    @classmethod
    def obtener_info_trabajo_curso(cls, orden_trabajo):
        """Obtiene información detallada del trabajo en curso."""
        from .models import RegistroTiempoReal  # ✅ Importar dentro
        
        registros = RegistroTiempoReal.objects.filter(
            orden_trabajo=orden_trabajo,
            estado='en_curso'
        ).select_related('empleado', 'servicio_orden__servicio')
        
        if not registros.exists():
            return None
        
        servicio_orden = registros.first().servicio_orden
        empleados = [r.empleado for r in registros]
        
        return {
            'servicio': servicio_orden,
            'servicio_nombre': servicio_orden.servicio.nombre if servicio_orden else 'Desconocido',
            'empleados': empleados,
            'cantidad_empleados': len(empleados)
        }

    @classmethod
    def iniciar_trabajo(cls, empleado, orden_trabajo, servicio_orden):
        from .models import RegistroTiempoReal, AsignacionOrden  # ✅ Importar dentro
        
        # Verificar si hay trabajo en curso en otro servicio diferente
        servicio_en_curso = cls.obtener_servicio_en_curso(orden_trabajo)
        
        if servicio_en_curso and servicio_en_curso.id != servicio_orden.id:
            return None, False, f"No se puede iniciar. Hay empleados trabajando en otro servicio."
        
        asignacion = AsignacionOrden.objects.filter(
            orden=orden_trabajo,
            servicio=servicio_orden,
            empleado=empleado
        ).first()
        
        if not asignacion:
            return None, False, "No se encontró la asignación para este servicio"
        
        if asignacion.registro_tiempo_real:
            registro_existente = asignacion.registro_tiempo_real
            if registro_existente.estado == 'en_curso':
                return registro_existente, False, "Ya tienes un trabajo en curso en este servicio"
            elif registro_existente.estado == 'pausado':
                servicio_curso = cls.obtener_servicio_en_curso(orden_trabajo)
                if servicio_curso and servicio_curso.id != servicio_orden.id:
                    return None, False, f"No se puede reanudar. Hay empleados trabajando en otro servicio."
                registro_existente.reanudar_trabajo()
                return registro_existente, True, "Trabajo reanudado"
            elif registro_existente.estado == 'finalizado':
                registro_existente.delete()
        
        registro = RegistroTiempoReal.objects.create(
            empleado=empleado,
            orden_trabajo=orden_trabajo,
            servicio_orden=servicio_orden
        )
        registro.iniciar_trabajo()
        
        asignacion.registro_tiempo_real = registro
        asignacion.save(update_fields=['registro_tiempo_real'])
        
        return registro, True, "Trabajo iniciado"

    @classmethod
    def finalizar_trabajo(cls, registro_id):
        from .models import RegistroTiempoReal  # ✅ Importar dentro
        
        try:
            registro = RegistroTiempoReal.objects.get(id=registro_id)
            if registro.estado == 'finalizado':
                return registro, False, "El trabajo ya estaba finalizado"
            
            registro.finalizar_trabajo()
            
            if registro.servicio_orden:
                tiempo_estimado = registro.servicio_orden.servicio.tiempo_min_estimado or 0
                if registro.minutos_trabajados > tiempo_estimado * 1.2:
                    return registro, True, f"ATENCIÓN: Excedió el tiempo estimado en {registro.minutos_trabajados - tiempo_estimado} minutos"
            
            return registro, True, "Trabajo finalizado"
        except RegistroTiempoReal.DoesNotExist:
            return None, False, "Registro no encontrado"
        except Exception as e:
            return None, False, str(e)

    @classmethod
    def pausar_trabajo(cls, registro_id):
        from .models import RegistroTiempoReal  # ✅ Importar dentro
        
        try:
            registro = RegistroTiempoReal.objects.get(id=registro_id)
            if registro.estado != 'en_curso':
                return registro, False, "El trabajo no está en curso"
            
            registro.pausar_trabajo()
            return registro, True, "Trabajo pausado"
        except RegistroTiempoReal.DoesNotExist:
            return None, False, "Registro no encontrado"
        except Exception as e:
            return None, False, str(e)

    @classmethod
    def reanudar_trabajo(cls, registro_id):
        from .models import RegistroTiempoReal  # ✅ Importar dentro
        
        try:
            registro = RegistroTiempoReal.objects.get(id=registro_id)
            if registro.estado != 'pausado':
                return registro, False, "El trabajo no está pausado"
            
            # Verificar si hay trabajo en curso en otro servicio diferente
            servicio_en_curso = cls.obtener_servicio_en_curso(registro.orden_trabajo)
            if servicio_en_curso and servicio_en_curso.id != registro.servicio_orden.id:
                return None, False, f"No se puede reanudar. Ya hay empleados trabajando en el servicio '{servicio_en_curso.servicio.nombre}'."
            
            registro.reanudar_trabajo()
            registro.refresh_from_db()
            return registro, True, "Trabajo reanudado"
        except RegistroTiempoReal.DoesNotExist:
            return None, False, "Registro no encontrado"
        except Exception as e:
            return None, False, str(e)
    
    @classmethod
    def obtener_tiempo_empleado_hoy(cls, empleado):
        from .models import RegistroTiempoReal  # ✅ Importar dentro
        from django.utils import timezone
        
        hoy = timezone.now().date()
        
        registros_hoy = RegistroTiempoReal.objects.filter(
            empleado=empleado,
            fecha_inicio__date=hoy,
            estado='finalizado'
        )
        
        total_minutos = sum(r.minutos_trabajados for r in registros_hoy)
        
        registros_curso = RegistroTiempoReal.objects.filter(
            empleado=empleado,
            fecha_inicio__date=hoy,
            estado='en_curso'
        )
        
        for registro in registros_curso:
            total_minutos += registro.minutos_transcurridos
        
        return total_minutos
    
    @staticmethod
    def minutos_a_hhmm(minutos):
        if minutos is None:
            return "00:00"
        try:
            minutos = int(float(minutos))
            horas = minutos // 60
            mins = minutos % 60
            return f"{horas:02d}:{mins:02d}"
        except (ValueError, TypeError):
            return "00:00"


class ValidacionAsignacionService:
    """Servicio para validar asignaciones antes de crearlas."""
    
    @classmethod
    def validar_disponibilidad_empleado(cls, empleado, orden, servicio):
        from .models import AsignacionOrden  # ✅ Importar dentro
        
        if AsignacionOrden.objects.filter(
            orden=orden,
            empleado=empleado,
            servicio=servicio
        ).exists():
            return False, "El empleado ya está asignado a este servicio"
        
        horas_info = ControlCargaService.calcular_horas_empleado(empleado)
        nuevo_tiempo = servicio.servicio.tiempo_min_estimado or 0
        nuevo_total = horas_info['minutos'] + nuevo_tiempo
        
        limite_minutos = (empleado.limite_horas_diarias or 8) * 60
        if empleado.limite_horas_diarias and nuevo_total > limite_minutos:
            return False, f"El empleado excedería su límite de {empleado.limite_horas_diarias}h"
        
        return True, "Válido"