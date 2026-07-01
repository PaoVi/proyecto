# insumo/forms.py
import re
from decimal import Decimal, InvalidOperation
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Insumo, SubInsumo, MovimientoStock, GrupoInsumo


def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _parse_money(value) -> Decimal:
    if value in (None, ""):
        raise InvalidOperation()

    s = str(value).strip()
    s = re.sub(r"(?i)\bgs\.?\b", "", s)
    s = s.replace(" ", "")

    m = re.search(r"([.,])(\d{1,2})$", s)
    decimals = ""
    if m:
        decimals = m.group(2)
        s = s[: m.start()]

    s = re.sub(r"\D", "", s)

    if s == "":
        int_part = "0"
    else:
        int_part = s

    if decimals:
        quantized = f"{int_part}.{decimals}"
    else:
        quantized = int_part

    try:
        return Decimal(quantized)
    except InvalidOperation:
        raise InvalidOperation()


class InsumoForm(forms.ModelForm):
    grupo = forms.ChoiceField(
        choices=GrupoInsumo.choices,
        label=_("Grupo"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text=_("Clasificación principal del insumo (define el prefijo del código)")
    )
    
    categoria = forms.CharField(
        label=_("Categoría"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'}),
        required=False,
    )

    tiene_garantia = forms.BooleanField(
        required=False,
        label=_("¿Tiene garantía?"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text=_("Marcar si este repuesto tiene garantía")
    )
    
    garantia_meses = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=60,
        label=_("Garantía (meses)"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '60'}),
        help_text=_("Duración de la garantía en meses (1 a 60)")
    )

    class Meta: 
        model = Insumo
        fields = [
            "nombre",
            "descripcion",
            "grupo",
            "categoria", 
            "unidad",
            "costo_unitario",
            "stock_minimo", 
            "tiene_garantia",   
            "garantia_meses",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "unidad": forms.Select(attrs={"class": "form-select"}),
            "costo_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "stock_minimo": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }
        error_messages = {
            "nombre": {"unique": _("Ya existe un insumo con este nombre.")},
            "stock_minimo": {"min_value": _("El stock mínimo no puede ser negativo.")},
            "costo_unitario": {"min_value": _("El costo no puede ser negativo.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nombre"].required = True
        self.fields["grupo"].required = True
        self.fields["costo_unitario"].required = True
        self.fields["unidad"].required = True 
        self.fields["stock_minimo"].required = True
        
        self.fields["descripcion"].required = False
        self.fields["categoria"].required = False

        if not self.instance.pk:
            self.instance.is_active = True
            # Stock actual siempre 0 en creación
            self.instance.stock_actual = 0

        if self.initial.get('categoria'):
            self.initial['categoria'] = self.initial['categoria'].upper()
        
        # Inicializar campos de garantía
        if self.instance and self.instance.pk:
            if self.instance.grupo == 'repuesto':
                # Si es repuesto, mostrar los campos
                self.fields['tiene_garantia'].initial = self.instance.tiene_garantia
                self.fields['garantia_meses'].initial = self.instance.garantia_meses
            else:
                # Si no es repuesto, ocultar los campos
                self.fields['tiene_garantia'].widget = forms.HiddenInput()
                self.fields['garantia_meses'].widget = forms.HiddenInput()
        
        # Configurar visibilidad dinámica (con JavaScript)
        if 'garantia_meses' in self.fields:
            self.fields['garantia_meses'].widget.attrs.update({
                'class': 'form-control garantia-meses-field',
            })
            # Si no es repuesto o no tiene garantía, ocultar inicialmente
            if not self.instance.pk or self.instance.grupo != 'repuesto' or not self.instance.tiene_garantia:
                self.fields['garantia_meses'].widget.attrs['style'] = 'display: none;'

    def _normalize(self):
        self.cleaned_data["nombre"] = _norm_spaces(self.cleaned_data.get("nombre"))
        self.cleaned_data["categoria"] = _norm_spaces(self.cleaned_data.get("categoria"))
        self.cleaned_data["unidad"] = _norm_spaces(self.cleaned_data.get("unidad"))
        desc = self.cleaned_data.get("descripcion")
        if desc is not None:
            self.cleaned_data["descripcion"] = desc.strip()

    def clean_nombre(self):
        nombre = _norm_spaces(self.cleaned_data.get("nombre"))
        if not nombre:
            raise ValidationError(_("Este campo es obligatorio."))

        qs = Insumo.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_("Ya existe un insumo con este nombre."))
        return nombre

    def clean_costo_unitario(self):
        raw = self.data.get(self.add_prefix("costo_unitario")) or self.cleaned_data.get("costo_unitario")
        try:
            value = _parse_money(raw)
        except InvalidOperation:
            raise ValidationError(_("Monto inválido. Ingrese un valor numérico."))
        if value < 0:
            raise ValidationError(_("El costo no puede ser negativo."))
        return value

    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data.get("stock_minimo")
        if stock_minimo in (None, ""):
            return 0
        try:
            stock_minimo = Decimal(str(stock_minimo))
        except (TypeError, ValueError):
            raise ValidationError(_("Ingrese un número válido."))
        if stock_minimo < 0:
            raise ValidationError(_("El stock mínimo no puede ser negativo."))
        return stock_minimo

    def clean_categoria(self):
        categoria = self.cleaned_data.get('categoria')
        if categoria:
            categoria = _norm_spaces(categoria.upper())
        return categoria

    def clean(self):
        cleaned_data = super().clean()
        grupo = cleaned_data.get('grupo')
        tiene_garantia = cleaned_data.get('tiene_garantia')
        garantia_meses = cleaned_data.get('garantia_meses')
        
        # Validaciones de garantía
        if grupo == 'repuesto':
            if tiene_garantia:
                if not garantia_meses:
                    self.add_error('garantia_meses', _("Debe especificar la duración de la garantía."))
                elif garantia_meses < 1 or garantia_meses > 60:
                    self.add_error('garantia_meses', _("La garantía debe ser entre 1 y 60 meses."))
            else:
                cleaned_data['garantia_meses'] = None
        else:
            # Si no es repuesto, limpiar garantía
            cleaned_data['tiene_garantia'] = False
            cleaned_data['garantia_meses'] = None
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asegurar que stock_actual sea 0 en creación
        if not instance.pk:
            instance.stock_actual = 0
        
        if commit:
            instance.save()
        
        return instance


# insumo/forms.py - InsumoEditarForm corregido

class InsumoEditarForm(forms.ModelForm):
    """Formulario para editar insumos - SIN stock_actual editable"""
    
    grupo = forms.ChoiceField(
        choices=GrupoInsumo.choices,
        label=_("Grupo"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
    )
    
    categoria = forms.CharField(
        label=_("Categoría"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'})
    )

    tiene_garantia = forms.BooleanField(
        required=False,
        label=_("¿Tiene garantía?"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text=_("Marcar si este repuesto tiene garantía")
    )
    
    garantia_meses = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=60,
        label=_("Garantía (meses)"),
        widget=forms.Select(attrs={'class': 'form-select'}),  # Cambiado a Select
        help_text=_("Duración de la garantía en meses")
    )

    class Meta:
        model = Insumo
        fields = [
            "nombre",
            "descripcion",
            "grupo",
            "categoria",
            "unidad",
            "costo_unitario",
            "stock_minimo",
            "tiene_garantia",
            "garantia_meses",
            "is_active"
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "unidad": forms.Select(attrs={"class": "form-select"}),
            "costo_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "stock_minimo": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        error_messages = {
            "nombre": {"unique": _("Ya existe un insumo con este nombre.")},
            "stock_minimo": {"min_value": _("El stock mínimo no puede ser negativo.")},
            "costo_unitario": {"min_value": _("El costo no puede ser negativo.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar opciones del select de garantía_meses
        self.fields['garantia_meses'].widget.choices = [
            ('', 'Seleccione la duración'),
            (1, '1 mes'),
            (3, '3 meses'),
            (6, '6 meses'),
            (12, '12 meses (1 año)'),
            (24, '24 meses (2 años)'),
            (36, '36 meses (3 años)'),
        ]
        
        # Mostrar stock actual como solo lectura
        if self.instance and self.instance.pk:
            self.fields['stock_actual_readonly'] = forms.CharField(
                label=_("Stock Actual"),
                initial=self.instance.stock_actual,
                widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
                required=False
            )
            # Insertar el campo después de stock_minimo
            field_list = list(self.fields.items())
            for i, (field_name, _field) in enumerate(field_list):
                if field_name == 'stock_minimo':
                    field_list.insert(i + 1, ('stock_actual_readonly', self.fields.pop('stock_actual_readonly')))
                    break
            from collections import OrderedDict
            self.fields = OrderedDict(field_list)
        
        # Configurar visibilidad de campos de garantía
        if self.instance and self.instance.pk:
            if self.instance.grupo == 'repuesto':
                # Si es repuesto, mostrar los campos con valores iniciales
                self.fields['tiene_garantia'].initial = self.instance.tiene_garantia
                self.fields['garantia_meses'].initial = self.instance.garantia_meses
                # Configurar para visibilidad dinámica con JS
                self.fields['garantia_meses'].widget.attrs.update({
                    'class': 'form-select garantia-meses-field',
                })
                if not self.instance.tiene_garantia:
                    self.fields['garantia_meses'].widget.attrs['style'] = 'display: none;'
            else:
                # Si no es repuesto, ocultar campos de garantía
                self.fields['tiene_garantia'].widget = forms.HiddenInput()
                self.fields['garantia_meses'].widget = forms.HiddenInput()
                self.fields['tiene_garantia'].initial = False
                self.fields['garantia_meses'].initial = None

    def clean_nombre(self):
        nombre = _norm_spaces(self.cleaned_data.get("nombre"))
        if not nombre:
            raise ValidationError(_("Este campo es obligatorio."))

        qs = Insumo.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_("Ya existe un insumo con este nombre."))
        return nombre

    def clean_costo_unitario(self):
        raw = self.cleaned_data.get("costo_unitario")
        if raw is None or raw == '':
            return 0
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            raise ValidationError(_("Monto inválido. Ingrese un valor numérico."))
        if value < 0:
            raise ValidationError(_("El costo no puede ser negativo."))
        return value

    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data.get("stock_minimo")
        if stock_minimo in (None, ""):
            return 0
        try:
            stock_minimo = Decimal(str(stock_minimo))
        except (TypeError, ValueError):
            raise ValidationError(_("Ingrese un número válido."))
        if stock_minimo < 0:
            raise ValidationError(_("El stock mínimo no puede ser negativo."))
        return stock_minimo

    def clean(self):
        cleaned_data = super().clean()
        grupo = cleaned_data.get('grupo')
        tiene_garantia = cleaned_data.get('tiene_garantia')
        garantia_meses = cleaned_data.get('garantia_meses')
        
        # Validaciones de garantía
        if grupo == 'repuesto':
            if tiene_garantia:
                if not garantia_meses:
                    self.add_error('garantia_meses', _("Debe especificar la duración de la garantía."))
                elif garantia_meses < 1 or garantia_meses > 12:
                    self.add_error('garantia_meses', _("La garantía debe ser entre 1 y 12 meses."))
            else:
                cleaned_data['garantia_meses'] = None
        else:
            # Si no es repuesto, limpiar garantía
            cleaned_data['tiene_garantia'] = False
            cleaned_data['garantia_meses'] = None
        
        return cleaned_data


# FORMULARIO PARA CREAR SUBINSUMOS
class CrearSubInsumosForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        label=_("Cantidad de subinsumos a crear"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    cantidad_por_subinsumo = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        initial=1,
        label=_("Cantidad por subinsumo"),
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.01',
            'min': '0.01'
        })
    )


# CONTROL DE STOCK
class MovimientoStockForm(forms.ModelForm):
    class Meta:
        model = MovimientoStock
        fields = ['insumo', 'tipo', 'cantidad', 'motivo', 'observaciones']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'min': '0.01'
            }),
            'motivo': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
            }),
        }


class AltaStockForm(forms.Form):
    MOTIVOS_ALTA = [
        ('compra', 'Compra'),
        ('ajuste', 'Ajuste de inventario'),
        ('produccion', 'Producción'),
        ('otros', 'Otros'),
    ]
    insumo = forms.ModelChoiceField(
        queryset=Insumo.objects.filter(is_active=True),
        label=_("Insumo"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cantidad = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        label=_("Cantidad a agregar"),
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.01',
            'min': '0.01'
        })
    )
    motivo = forms.ChoiceField(
        choices=MOTIVOS_ALTA,
        initial='compra',
        label=_("Motivo"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    observaciones = forms.CharField(
        required=False,
        label=_("Observaciones"),
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3
        })
    )


class BajaStockForm(forms.Form):
    MOTIVOS_BAJA = [
        ('venta', 'Venta/Servicio'),
        ('ajuste', 'Ajuste de inventario'),
        ('danado', 'Dañado/Perdido'),
        ('otros', 'Otros'),
    ]
    insumo = forms.ModelChoiceField(
        queryset=Insumo.objects.filter(is_active=True),
        label=_("Insumo"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cantidad = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        label=_("Cantidad a retirar"),
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.01',
            'min': '0.01'
        })
    )
    motivo = forms.ChoiceField(
        choices=MOTIVOS_BAJA,
        initial='venta',
        label=_("Motivo"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    observaciones = forms.CharField(
        required=True,
        label=_("Observaciones"),
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': _('Observaciones...')
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        insumo = cleaned_data.get('insumo')
        cantidad = cleaned_data.get('cantidad')
        
        if insumo and cantidad:
            # SOLO validar stock físico total aquí
            stock_fisico = insumo.stock_fisico_real
            if cantidad > stock_fisico:
                self.add_error(
                    'cantidad', 
                    _("No hay suficiente stock disponible. Stock actual: %(stock)s %(unidad)s") % {
                        'stock': stock_fisico,
                        'unidad': insumo.get_unidad_display()
                    }
                )
        
        return cleaned_data