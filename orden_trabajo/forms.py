from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.forms.models import BaseInlineFormSet
import calendar, re
from datetime import timedelta, date
from .models import OrdenTrabajo, OrdenServicio, AsignacionOrden
from empleado.models import Empleado


# Estados de la Orden de Trabajo
ESTADOS_ORDEN = (
    ('pendiente', 'Pendiente'),
    ('espera_repuestos', 'Espera Repuestos'),
    ('en_proceso', 'En Proceso'),
    ('pausado', 'Pausado'),
    ('completado', 'Completado'),
    ('en_revision', 'En Revisión'),  
    ('aprobado', 'Aprobado'),    
    ('rechazado', 'Rechazado'),     
    ('facturado', 'Facturado'),
    ('cancelado', 'Cancelado'),
)

# Transiciones permitidas entre estados
TRANSICIONES_PERMITIDAS = {
    'pendiente': ['espera_repuestos', 'en_proceso', 'cancelado'],
    'espera_repuestos': ['en_proceso', 'pausado', 'cancelado'],
    'en_proceso': ['espera_repuestos', 'pausado', 'completado', 'cancelado'],
    'pausado': ['espera_repuestos', 'en_proceso', 'cancelado'],
    'completado': ['en_revision'],  
    'en_revision': ['aprobado', 'rechazado'],  
    'aprobado': ['facturado'],  
    'rechazado': ['en_proceso'], 
    'facturado': [],
    'cancelado': [],
}


# Estados que no permiten edición
ESTADOS_BLOQUEADOS = ['facturado', 'cancelado', 'aprobado']

class RevisionServicioForm(forms.Form):
    """Formulario para revisar un servicio individual"""
    aprobado = forms.ChoiceField(
        choices=[('aprobado', 'Aprobar'), ('rechazado', 'Rechazar')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Decisión"
    )
    observacion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        required=False,
        label="Observación / Motivo del rechazo"
    )

class FriendlyDateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", ["%d%m%Y", "%d/%m/%Y", "%d-%m-%Y"])
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return super().to_python(value)

        raw = str(value).strip()
        
        if '/' in raw or '-' in raw:
            return super().to_python(raw)
            
        digits = re.sub(r"\D+", "", raw)

        if digits.isdigit() and len(digits) == 8:
            try:
                day = int(digits[:2])
                month = int(digits[2:4])
                year = int(digits[4:])
            except ValueError:
                raise ValidationError(_("Formato inválido. Use DDMMYYYY, DD/MM/YYYY o DD-MM-YYYY"))
        else:
            return super().to_python(raw)

        self._validar_dia_mes(year, month, day)

        try:
            return date(year, month, day)
        except ValueError:
            raise ValidationError(_("Fecha inválida. Use el formato DD/MM/YYYY."))

    def _validar_dia_mes(self, year, month, day):
        if not (1 <= month <= 12):
            raise ValidationError(_("Ingrese un mes válido [01-12]."))

        max_dia_mes = calendar.monthrange(year, month)[1]

        if month == 2 and day == 29 and not calendar.isleap(year):
            raise ValidationError(
                _("El año %(year)s no es bisiesto; no se permite el 29 de febrero."),
                params={"year": year}
            )

        if day > max_dia_mes:
            if month == 2:
                raise ValidationError(
                    _("Febrero de %(year)s sólo tiene %(max)s días."),
                    params={"year": year, "max": max_dia_mes}
                )
            elif max_dia_mes == 30:
                raise ValidationError(_("El mes ingresado solo tiene 30 días."))
            else:
                raise ValidationError(_("El mes ingresado solo tiene 31 días."))
            

class OrdenTrabajoForm(forms.ModelForm):
    """Formulario para crear Orden de Trabajo"""
    
    class Meta:
        model = OrdenTrabajo
        fields = ["cliente", "vehiculo", "descripcion"]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "vehiculo": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
        labels = {"descripcion": "Descripción / Observaciones"}
    
    def save(self, commit=True):
        # Al crear, el estado por defecto es 'pendiente'
        instance = super().save(commit=False)
        if not instance.pk:  # Solo si es nuevo
            instance.estado = 'pendiente'
        if commit:
            instance.save()
        return instance


class OrdenTrabajoEditarForm(forms.ModelForm):
    """Formulario para editar Orden de Trabajo con validación de estados"""
    estado = forms.ChoiceField(
        choices=ESTADOS_ORDEN,
        required=False,  # ← ESTA ES LA CLAVE
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    class Meta:
        model = OrdenTrabajo
        fields = ["descripcion", "estado"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select form-select-sm"}, choices=ESTADOS_ORDEN),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Si la orden está en estado bloqueado, hacer todos los campos readonly
        if instance and instance.estado in ESTADOS_BLOQUEADOS:
            for field in self.fields:
                self.fields[field].disabled = True
                self.fields[field].widget.attrs['readonly'] = True
    
    def clean(self):
        cleaned_data = super().clean()
        instance = self.instance
        
        # Si es una orden nueva, no hay validación de transición
        if not instance.pk:
            return cleaned_data
        
        nuevo_estado = cleaned_data.get('estado')
        estado_actual = instance.estado
        
        # Validar si la orden está bloqueada
        if estado_actual in ESTADOS_BLOQUEADOS:
            raise ValidationError(
                f"No se puede modificar una orden en estado '{self._get_estado_display(estado_actual)}'."
            )
        
        # Validar transición de estado
        if nuevo_estado and nuevo_estado != estado_actual:
            if nuevo_estado not in TRANSICIONES_PERMITIDAS.get(estado_actual, []):
                raise ValidationError(
                    f"No se puede cambiar de '{self._get_estado_display(estado_actual)}' "
                    f"a '{self._get_estado_display(nuevo_estado)}'. "
                    f"Transiciones permitidas: {', '.join([self._get_estado_display(e) for e in TRANSICIONES_PERMITIDAS[estado_actual]])}"
                )
        
        return cleaned_data
    
    def _get_estado_display(self, estado):
        """Obtener el display name del estado"""
        for codigo, display in ESTADOS_ORDEN:
            if codigo == estado:
                return display
        return estado


class OrdenServicioForm(forms.ModelForm):
    """Formulario para servicios dentro de una OT"""
    
    class Meta:
        model = OrdenServicio
        fields = ["servicio", "cantidad", "precio_unitario"]
        widgets = {
            "servicio": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control form-control-sm", "min": "0.01", "step": "0.01"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control form-control-sm", "min": "0", "step": "0.01"}),
        }
        labels = {"precio_unitario": "Precio unitario"}

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is None or float(cantidad) <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0.")
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get("precio_unitario")
        if precio is None or float(precio) < 0:
            raise ValidationError("El precio unitario no puede ser negativo.")
        return precio


# FormSet para servicios
OrdenServicioFormSet = inlineformset_factory(
    parent_model=OrdenTrabajo,
    model=OrdenServicio,
    form=OrdenServicioForm,
    extra=0,
    can_delete=True,
    validate_min=True,
    min_num=1,  # exigir al menos un servicio
)


class AsignacionOrdenForm(forms.ModelForm):
    """
    Form para asignar empleados a la orden.
    """
    empleado = forms.ModelChoiceField(
        queryset=Empleado.objects.all(),  
        label="Empleado",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        empty_label="— Seleccione —",
        help_text="Se priorizan quienes tienen menos OTs abiertas.",
    )

    def __init__(self, *args, **kwargs):
        orden = kwargs.pop("orden", None)
        super().__init__(*args, **kwargs)

        # Obtener empleados activos - CAMBIO AQUÍ: usar 'estado' en lugar de 'activo'
        base_qs = Empleado.objects.filter(estado=True)

        # Anotar cuántas OTs abiertas tiene cada empleado
        base_qs = base_qs.annotate(
            ots_abiertas=Count(
                "asignaciones",
                filter=Q(
                    asignaciones__orden__estado__in=["pendiente", "en_proceso", "espera_repuestos", "pausado"],
                ),
                distinct=True,
            )
        )

        # Evitar duplicar empleados ya asignados en esta OT
        if orden is not None:
            base_qs = base_qs.exclude(
                asignaciones__orden=orden,
                asignaciones__orden__estado__in=["pendiente", "en_proceso", "espera_repuestos", "pausado"],
            )

        # Ordenar por menos OTs abiertas primero
        self.fields["empleado"].queryset = base_qs.order_by("ots_abiertas", "nombre")

    class Meta:
        model = AsignacionOrden
        fields = ("empleado",)