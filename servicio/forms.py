from decimal import Decimal, InvalidOperation
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Servicio
import re


def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ["nombre", "descripcion", "categoria", "mano_obra", "tiempo_min_estimado", "comision_porcentaje"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "categoria": forms.TextInput(attrs={"class": "form-control", "style": "text-transform: uppercase;"}),
            "mano_obra": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "tiempo_min_estimado": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "comision_porcentaje": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100", "placeholder": "Ej.: 10, 15.50"
            }),
        }
        error_messages = {
            "nombre": {
                "unique": _("Ya existe un servicio con este nombre.")},
            'insumo': {
                'required': _("Este campo es obligatorio."),
            },
            'cantidad': {
                'required': _("Este campo es obligatorio."),
                'invalid':  _("Ingrese un número válido"),
                'min_value': _("Cantidad debe ser mayor a 0.00"),
            },
            'tiempo_min_estimado': {
                'required': _("Este campo es obligatorio."),
            },
            'comision_porcentaje': {
                'invalid': _("Ingrese un porcentaje válido (0-100)"),
                'min_value': _("El porcentaje no puede ser negativo"),
                'max_value': _("El porcentaje no puede ser mayor a 100%"),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Requeridos
        self.fields["nombre"].required = True
        self.fields["mano_obra"].required = True
        self.fields["tiempo_min_estimado"].required = True
        self.fields["categoria"].required = True
        
        # Asegurar que la categoría se muestre en mayúsculas
        if self.initial.get('categoria'):
            self.initial['categoria'] = self.initial['categoria'].upper()

    def clean_categoria(self):
        categoria = self.cleaned_data.get('categoria')
        if categoria:
            # Convertir a mayúsculas y normalizar espacios
            categoria = _norm_spaces(categoria.upper())
        return categoria

    def clean_tiempo_min_estimado(self):
        """Validar que el tiempo mínimo estimado sea mayor a 0"""
        tiempo_min_estimado = self.cleaned_data.get('tiempo_min_estimado')
        
        if tiempo_min_estimado is not None and tiempo_min_estimado < 1:
            self.add_error('tiempo_min_estimado', _('El tiempo mínimo debe ser mayor a 00:00.'))
        
        return tiempo_min_estimado

    def clean_comision_porcentaje(self):
        comision = self.cleaned_data.get('comision_porcentaje')
        
        # Si está vacío, usar el valor por defecto
        if comision is None:
            return None
            
        # Validar rango
        if comision < 0:
            raise ValidationError(_("El % de comisión no puede ser negativo."))
            
        if comision > 100:
            raise ValidationError(_("El % de comisión no puede ser mayor a 100%."))
            
        return comision
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que haya al menos 1 insumo
        insumos_encontrados = False
        
        # Contar insumos existentes NO eliminados
        insumos_existentes_no_eliminados = 0
        
        # Buscar insumos existentes
        i = 0
        while True:
            insumo_key = f'insumos_existentes[{i}][insumo_id]'
            if insumo_key not in self.data:
                break
                
            insumo_id = self.data.get(insumo_key, '').strip()
            if insumo_id:
                # Verificar si NO está en la lista de eliminados
                eliminado = False
                insumos_eliminados = self.data.getlist('insumos_eliminados[]')
                if insumo_id in insumos_eliminados:
                    eliminado = True
                    
                if not eliminado:
                    insumos_existentes_no_eliminados += 1
                    insumos_encontrados = True
                    
            i += 1
        
        # Si no hay insumos existentes, buscar nuevos
        if not insumos_encontrados:
            i = 0
            while f'insumos_nuevos[{i}][insumo_id]' in self.data:
                insumo_id = self.data.get(f'insumos_nuevos[{i}][insumo_id]', '').strip()
                cantidad_str = self.data.get(f'insumos_nuevos[{i}][cantidad]', '0').strip()
                
                if insumo_id and cantidad_str:
                    try:
                        cantidad = Decimal(cantidad_str)
                        if cantidad > 0:
                            insumos_encontrados = True
                            break
                    except (InvalidOperation, ValueError):
                        pass
                i += 1

        # Validar que haya al menos 1 insumo
        if not insumos_encontrados:
            self.add_error('descripcion', _('El servicio debe tener al menos un insumo.'))
        
        return cleaned_data

class ServicioEditarForm(ServicioForm):
    class Meta(ServicioForm.Meta):
        fields = ServicioForm.Meta.fields + ["is_active", "comision_porcentaje"]
        widgets = {
            **ServicioForm.Meta.widgets,
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }