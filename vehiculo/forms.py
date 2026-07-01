import re
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Vehiculo
from cliente.models import Cliente

# NORMALIZACIONES
PLATE_SUGGESTIONS = [
    r"^[A-Z]{3}\d{3}$",   # ABC123 (antigua PY)
    r"^[A-Z]{3}\d{4}$",   # ABC1234 (Mercosur)
]

VIN_RE = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')          # VIN moderno (sin I,O,Q)
LEGACY_CHASIS_RE = re.compile(r'^[A-HJ-NPR-Z0-9]{9,14}$')  # chasis antiguos

def _upcase_compact(v: str) -> str:
    """Mayúsculas + sin espacios internos."""
    return re.sub(r'\s+', '', (v or '').strip().upper())


class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = [
            "marca", "modelo", "anio", "color",
            "nro_chapa", "nro_chasis",
            "cantidad_puerta", "motor_cilindrada",
            "tipo_combustible", "uso",
            "cedula_verde", "via_importacion", "procedencia", "tipo_transmision",
            "alarma", "gps", "propietario", "poseedor"
        ]
        widgets = {
            "propietario": forms.Select(attrs={
                "class": "form-control",
                "placeholder": "Dueño legal",
                }),
            "poseedor": forms.Select(attrs={
                "class": "form-control",
                "placeholder": "Persona que usa/maneja",
                }),
            "marca": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "anio": forms.NumberInput(attrs={"class": "form-control", "inputmode": "numeric"}),
            "color": forms.TextInput(attrs={"class": "form-control"}),

            "nro_chapa": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej.: ABC123 o ABC1234",
            }),
            "nro_chasis": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "VIN 17 caracteres o chasis antiguo",
            }),

            "cantidad_puerta": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "motor_cilindrada": forms.TextInput(attrs={"class": "form-control"}),

            "tipo_combustible": forms.Select(attrs={"class": "form-select"}),
            "uso": forms.Select(attrs={"class": "form-select"}),
            "cedula_verde": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "via_importacion": forms.Select(attrs={"class": "form-select"}),
            "procedencia": forms.Select(attrs={"class": "form-select"}),
            "tipo_transmision": forms.Select(attrs={"class": "form-select"}),

            "alarma": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "gps": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        help_texts = {
            "nro_chapa": _("Sugerido PY: ABC123 o ABC1234. También se admiten otros formatos alfanuméricos."),
            "nro_chasis": _("Use VIN (17 caracteres, sin I/O/Q). Si es antiguo, 9–14 caracteres válidos."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo clientes activos y ordenar alfabéticamente
        try:
            clientes_activos = Cliente.objects.filter(estado='activo').order_by('nombre')
        except:
            clientes_activos = Cliente.objects.all().order_by('nombre')
            
        # Usar 'propietario' y 'poseedor' en lugar de 'cliente'
        self.fields['propietario'].queryset = clientes_activos
        self.fields['poseedor'].queryset = clientes_activos
        
        # Hacer los campos no obligatorios
        self.fields['propietario'].required = False
        self.fields['poseedor'].required = False

        # DEFINIR CAMPOS OBLIGATORIOS/OPCIONALES
        # Campos OBLIGATORIOS
        campos_obligatorios = [
            'marca', 'modelo', 'anio', 'color',  'nro_chasis', 'uso',
            'tipo_combustible', 'via_importacion', 'procedencia', 'tipo_transmision'
        ]
        
        for campo in campos_obligatorios:
            self.fields[campo].required = True
        
        # Campos OPCIONALES
        campos_opcionales = [
            'nro_chapa', 'cantidad_puerta', 'motor_cilindrada', 
            'cedula_verde', 'alarma', 'gps', 'propietario', 'poseedor'
        ]
        
        for campo in campos_opcionales:
            self.fields[campo].required = False

        # Asegurar que los campos de selección muestren el valor actual
        if self.instance and self.instance.pk:
            # Establecer el valor inicial para campos de selección
            for field_name in ['tipo_combustible', 'uso', 'via_importacion', 'procedencia', 'tipo_transmision']:
                if hasattr(self.instance, field_name):
                    current_value = getattr(self.instance, field_name)
                    if current_value:
                        self.fields[field_name].initial = current_value


    def clean_nro_chapa(self):
        v = _upcase_compact(self.cleaned_data.get("nro_chapa"))
        # Sugerimos formatos PY, pero no bloqueamos otros (modelo se encarga con su validador laxo).
        return v

    def clean_nro_chasis(self):
        v = _upcase_compact(self.cleaned_data.get("nro_chasis"))
        # Aceptar VIN 17 o legacy 9–14 (sin I,O,Q). Si no calza, el validador del modelo levantará error.
        if VIN_RE.match(v) or LEGACY_CHASIS_RE.match(v):
            return v
        # Devolver igualmente normalizado y dejar que el modelo lo rechace con su mensaje.
        return v


class VehiculoEditarForm(VehiculoForm):
    estado = forms.BooleanField(
        required=False,
        label=_("Estado (Activo/Inactivo)"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta(VehiculoForm.Meta):
        fields = [
            "marca", "modelo", "anio", "color",
            "nro_chapa", "nro_chasis",
            "cantidad_puerta", "motor_cilindrada",
            "tipo_combustible", "uso",
            "cedula_verde", "via_importacion", "procedencia", "tipo_transmision",
            "alarma", "gps", "estado" 
        ]

    def __init__(self, *args, **kwargs):
        super(VehiculoForm, self).__init__(*args, **kwargs) 
        
        # Remueve explícitamente los campos propietario y poseedor
        if 'propietario' in self.fields:
            del self.fields['propietario']
        if 'poseedor' in self.fields:
            del self.fields['poseedor']
            
        self.fields["estado"].required = False

        # Asegurar que los campos de selección muestren el valor actual
        if self.instance and self.instance.pk:
            # Establecer el valor inicial para campos de selección
            for field_name in ['tipo_combustible', 'uso', 'via_importacion', 'procedencia', 'tipo_transmision']:
                if hasattr(self.instance, field_name):
                    current_value = getattr(self.instance, field_name)
                    if current_value:
                        self.fields[field_name].initial = current_value

    
class VehiculoVincularClienteForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(is_active=True),
        required=True,
        label="Cliente"
    )

    def __init__(self, *args, **kwargs):
        self.vehiculo = kwargs.pop('vehiculo', None)
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.filter(is_active=True)