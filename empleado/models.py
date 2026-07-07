from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, EmailValidator, MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date
import calendar
from django.conf import settings


cedula_ruc_validator = RegexValidator(
    regex=r"^[0-9]{5,12}(-[0-9]{1})?$",
    message=_("Formato inválido. Ej.: 1234567 o 80012345-1"),
)

telefono_py_validator = RegexValidator(
    regex=r"^\+?595[0-9]{7,9}$",
    message=_("Formato recomendado: +595xxxxxxx"),
)


class Empleado(models.Model):
    id_empleado = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150, verbose_name=_("Nombre Completo"))

    cedula_ruc = models.CharField(
        max_length=20,
        unique=True,
        validators=[cedula_ruc_validator],
        verbose_name=_("Cédula/RUC"),
        help_text=_("Ej.: 1234567 o 80012345-1"),
        error_messages={
            "unique": _("Ya existe un empleado con esta Cédula/RUC."),
        },
    )

    fecha_nacimiento = models.DateField(
        verbose_name=_("Fecha de nacimiento"),
    )

    telefono = models.CharField(
        max_length=20,
        validators=[telefono_py_validator],
        verbose_name=_("Teléfono"),
    )

    direccion = models.TextField(
        verbose_name=_("Dirección"),
    )

    ciudad = models.CharField(
        max_length=100,
        verbose_name=_("Ciudad"),
    )

    correo_electronico = models.EmailField(
        validators=[EmailValidator(message=_("Correo inválido"))],
        verbose_name=_("Correo electrónico"),
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Fecha de registro"),
    )

    fecha_ingreso = models.DateField(
        verbose_name=_("Fecha de ingreso"),
    )

    cargo = models.CharField(
        max_length=100,
        verbose_name=_("Cargo"),
    )

    salario_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Salario base"),
    )

    estado = models.BooleanField(
        default=True,
        verbose_name=_("Activo"),
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Fecha de actualización"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='empleado'  
    )

    limite_horas_diarias = models.PositiveIntegerField(
        _("Límite de horas diarias"),
        default=9,
        help_text=_("Horas máximas de trabajo por día para alertas de sobrecarga")
    )

    comision_acumulada = models.DecimalField(
        _("Comisión acumulada"),
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text=_("Comisiones acumuladas de servicios completados")
    )
    comision_por_cobrar = models.DecimalField(
        _("Comisión por cobrar"),
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text=_("Comisiones pendientes de pago (de órdenes completadas/facturadas)")
    )
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )
    
    class Meta:
        verbose_name = _("Empleado")
        verbose_name_plural = _("Empleados")
        ordering = ("-fecha_registro",)
        permissions = [
            ("gestionar_empleados", "Puede gestionar empleados"),
            ("ver_empleados", "Puede ver empleados"),
            ("agregar_empleados", "Puede registrar empleados"),
            ("editar_empleados", "Puede actualizar empleados"),
            ("desactivar_empleados", "Puede desactivar empleados"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.cedula_ruc})"

    def horas_activas(self):
        """
        Calcula las horas totales de servicios asignados al empleado
        SOLO en órdenes ACTIVAS (en_proceso) Y donde el trabajo REAL esté en curso
        """
        from django.db.models import Sum
        from orden_trabajo.models import AsignacionOrden
        
        estados_activos = ['en_proceso']
        
        # Sumar tiempos de servicios en órdenes activas asignadas al empleado
        # SOLO si el empleado NO está liberado Y el trabajo REAL está en curso
        total_minutos = AsignacionOrden.objects.filter(
            empleado=self,
            orden__estado__in=estados_activos,
            estado__in=['asignado', 'en_ejecucion']
        ).exclude(
            # Excluir asignaciones donde el registro de tiempo REAL está pausado o finalizado
            registro_tiempo_real__estado__in=['pausado', 'finalizado']
        ).aggregate(
            total=Sum('servicio__servicio__tiempo_min_estimado')
        )['total'] or 0
        
        return total_minutos / 60
    
    @property
    def estado_carga(self):
        """
        Retorna el estado de carga del empleado con nivel de alerta
        Considera TODAS las órdenes activas del empleado
        """
        horas = self.horas_activas()
        limite = self.limite_horas_diarias or 9  # Por defecto 8 horas
        
        # Calcular formato HH:MM
        total_minutos = int(horas * 60)
        horas_enteras = total_minutos // 60
        minutos_restantes = total_minutos % 60
        horas_formateadas = f"{horas_enteras:02d}:{minutos_restantes:02d}"
        
        porcentaje = (horas / limite) * 100 if limite > 0 else 0
        
        # Calcular minutos restantes
        minutos_restantes_totales = max(0, (limite - horas) * 60)
        restante_horas = int(minutos_restantes_totales // 60)
        restante_minutos = int(minutos_restantes_totales % 60)
        restante_formateado = f"{restante_horas:02d}:{restante_minutos:02d}"
        
        if horas >= limite:
            nivel = 'peligro'
            mensaje = f'¡SOBRECARGADO! {horas_formateadas}h / {limite}h'
        elif horas >= limite * 1:  # 100% del límite
            nivel = 'advertencia'
            mensaje = f'Cerca del límite: {horas_formateadas}h / {limite}h'
        elif horas >= limite * 0.8:  # 80% del límite
            nivel = 'info'
            mensaje = f'Carga media: {horas_formateadas}h / {limite}h'
        else:
            nivel = 'normal'
            mensaje = f'Disponible: {horas_formateadas}h / {limite}h'
        
        return {
            'horas': horas,
            'horas_formateadas': horas_formateadas,
            'limite': limite,
            'porcentaje': porcentaje,
            'nivel': nivel,
            'nivel_alerta': nivel,
            'mensaje': mensaje,
            'minutos_restantes': minutos_restantes_totales,
            'minutos_restantes_formateados': restante_formateado,
            'sobrecargado': horas >= limite
        }
    
    def horas_trabajadas_reales(self, fecha_inicio=None, fecha_fin=None):
        """
        Calcula las horas REALES trabajadas por el empleado (con inicio/fin registrados)
        Suma todos los registros de tiempo con fecha de inicio y fin
        """
        from django.db.models import Sum
        from orden_trabajo.models import RegistroTiempoReal
        
        queryset = RegistroTiempoReal.objects.filter(empleado=self)
        
        if fecha_inicio:
            queryset = queryset.filter(fecha_inicio__date__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_fin__date__lte=fecha_fin)
        
        total_minutos = queryset.aggregate(
            total=Sum('minutos_trabajados')
        )['total'] or 0
        
        return total_minutos / 60

    # Reglas de negocio / calendario 
    def clean(self):
        super().clean()
        hoy = date.today()

        def validar_dia_por_mes(fecha, field_name):
            """Valida días válidos por mes y 29/02 en años no bisiestos."""
            if not fecha:
                return
            max_dia_mes = calendar.monthrange(fecha.year, fecha.month)[1]
            if fecha.month == 2 and fecha.day == 29 and not calendar.isleap(fecha.year):
                raise ValidationError({
                    field_name: _("El año %(y)s no es bisiesto; no se permite el 29 de febrero.") % {"y": fecha.year}
                })
            if fecha.day > max_dia_mes:
                if fecha.month == 2:
                    raise ValidationError({
                        field_name: _("Febrero de %(y)s sólo tiene %(m)s días.") % {"y": fecha.year, "m": max_dia_mes}
                    })
                elif max_dia_mes == 30:
                    raise ValidationError({field_name: _("El mes ingresado solo tiene 30 días.")})
                else:
                    raise ValidationError({field_name: _("El mes ingresado solo tiene 31 días.")})

        # fecha_nacimiento: no futuro, >= 1900, mayor de 18, y día/mes válidos
        if self.fecha_nacimiento:
            if self.fecha_nacimiento > hoy:
                raise ValidationError({"fecha_nacimiento": _("La fecha de nacimiento no puede ser mayor a la fecha actual.")})
            if self.fecha_nacimiento.year < 1900:
                raise ValidationError({"fecha_nacimiento": _("La fecha de nacimiento es demasiado antigua.")})
            validar_dia_por_mes(self.fecha_nacimiento, "fecha_nacimiento")

            edad = hoy.year - self.fecha_nacimiento.year - (
                (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
            if edad < 18:
                raise ValidationError({"fecha_nacimiento": _("El empleado debe ser mayor de 18 años.")})

        # fecha_ingreso: requerida, no futuro, lógico vs nacimiento, y día/mes válidos
        if not self.fecha_ingreso:
            return 

        if self.fecha_ingreso > hoy:
            raise ValidationError({"fecha_ingreso": _("La fecha de ingreso no puede ser mayor a la fecha actual.")})

        validar_dia_por_mes(self.fecha_ingreso, "fecha_ingreso")

        if self.fecha_nacimiento and self.fecha_ingreso <= self.fecha_nacimiento:
            raise ValidationError({"fecha_ingreso": _("La fecha de ingreso debe ser posterior a la fecha de nacimiento.")})

        # salario_base: reforzar no-negativo y no-cero (además del validador de campo)
        if self.salario_base is not None:
            if self.salario_base < 0:
                raise ValidationError({"salario_base": _("El salario no puede ser negativo.")})
            if self.salario_base == 0:
                raise ValidationError({"salario_base": _("El salario no puede ser 0 Gs.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)