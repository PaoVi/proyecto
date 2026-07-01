# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, trailing-whitespace
# pylint: disable=no-member
# pylint: disable=unused-import
# pylint: disable=bare-except
from decimal import Decimal
from typing import Optional
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from factura.models import Factura, FacturaServicio, FacturaInsumo

# Configuración de impresión
try:
    from seguridad.models import ConfiguracionSistema
    HAS_CONFIG = True
except ImportError:
    ConfiguracionSistema = None
    HAS_CONFIG = False

IVA_CHOICES = (("10", "10 %"), ("5", "5 %"), ("0", "Exento"))

class FacturaEmitirForm(forms.ModelForm):
    configuracion_impresion = forms.ModelChoiceField(
        queryset=ConfiguracionSistema.objects.all(),
        required=False
    )
    # Datos del cliente (seleccionado desde búsqueda)
    cliente_id = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    cliente_ruc = forms.CharField(
        label=_("RUC"),
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly"
        }),
        required=True
    )
    
    cliente_nombre = forms.CharField(
        label=_("Nombre/Razón Social"),
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "readonly": "readonly"
        }),
        required=True
    )
    
    cliente_direccion = forms.CharField(
        label=_("Dirección"),
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly"
        }),
        required=False
    )
    
    cliente_telefono = forms.CharField(
        label=_("Teléfono"),
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly"
        }),
        required=False
    )

    # Datos de la factura
    fecha = forms.DateField(
        label=_("Fecha de Emisión"),
        widget=forms.DateInput(attrs={
            "type": "date", 
            "class": "form-control"
        }),
        initial=timezone.localdate,
        help_text=_("Debe ser hoy o una fecha futura."),
    )

    numero_factura = forms.CharField(
        label=_("Número de Factura"),
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly"
        }),
        required=True
    )

    timbrado = forms.CharField(
        label=_("Timbrado"),
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly"
        }),
        required=True
    )

    valido_hasta = forms.CharField(
        label=_("Válido hasta"),
        widget=forms.TextInput(attrs={
            "type": "month",
            "class": "form-control",
            "readonly": "readonly",
            "format": "dd/mm/yyyy"
        }),
        required=True
    )

    condicion_venta = forms.ChoiceField(
        label=_("Condición de Venta"),
        choices=(("contado", "Contado"), ("credito", "Crédito")),
        initial="contado",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"})
    )

    iva = forms.ChoiceField(
        label=_("IVA"),
        choices=IVA_CHOICES,
        initial="10",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    observaciones = forms.CharField(
        label=_("Observaciones"),
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control", 
            "rows": 2,
            "placeholder": _("Observaciones adicionales...")
        }),
    )

    # Configuración de impresión (desde Seguridad)
    if HAS_CONFIG:
        configuracion_impresion = forms.ModelChoiceField(
            label=_("Configuración de impresión"),
            required=False,
            queryset=ConfiguracionSistema.objects.filter(
                activo=True, 
                grupo__in=["impresion_factura", "facturacion", "plantilla_factura"]
            ).order_by("grupo", "clave"),
            widget=forms.Select(attrs={"class": "form-select"}),
            empty_label=_("— Seleccionar —"),
            help_text=_("Cargado desde Seguridad."),
        )
    else:
        configuracion_impresion = forms.CharField(
            label=_("Configuración de impresión"),
            required=False,
            help_text=_("Campo libre (no se encontró la app Seguridad)."),
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )

    class Meta:
        model = Factura
        fields = [
            "fecha", "iva", "observaciones"
        ]

    def __init__(self, *args, **kwargs):
        # Obtener datos iniciales para configuración del sistema
        initial = kwargs.get('initial', {})
        
        # Configurar datos por defecto
        if not initial.get('fecha'):
            initial['fecha'] = timezone.localdate()
            
        # Obtener configuración del sistema
        try:
            if HAS_CONFIG:
                config = ConfiguracionSistema.objects.filter(activo=True).first()
                if config:
                    if not initial.get('timbrado'):
                        initial['timbrado'] = getattr(config, 'timbrado', '')
                    if not initial.get('valido_hasta'):
                        if hasattr(config, 'valido_hasta') and config.valido_hasta:
                            initial['valido_hasta'] = config.valido_hasta.strftime("%Y-%m")
        except:
            pass
            
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    # --- Validaciones ---
    def clean_fecha(self):
        fecha = self.cleaned_data.get("fecha")
        if fecha and fecha < timezone.localdate():
            raise ValidationError(_("La fecha de la factura no puede ser menor a la fecha actual."))
        return fecha

    def clean_cliente_ruc(self):
        ruc = self.cleaned_data.get("cliente_ruc")
        if not ruc:
            raise ValidationError(_("El RUC del cliente es obligatorio."))
        if len(ruc) < 6:
            raise ValidationError(_("El RUC debe tener al menos 6 dígitos."))
        return ruc

    def clean_cliente_nombre(self):
        nombre = self.cleaned_data.get("cliente_nombre")
        if not nombre:
            raise ValidationError(_("El nombre del cliente es obligatorio."))
        return nombre

    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que se haya seleccionado un cliente
        if not cleaned_data.get('cliente_ruc') or not cleaned_data.get('cliente_nombre'):
            raise ValidationError(_("Debe seleccionar un cliente válido."))

        return cleaned_data

    def save(self, commit=True):
        # Crear instancia de Factura pero no guardar aún
        factura = super().save(commit=False)
        
        # Asignar datos del cliente a los nuevos campos
        factura.cliente_ruc = self.cleaned_data.get('cliente_ruc', '')
        factura.cliente_nombre = self.cleaned_data.get('cliente_nombre', '')
        factura.cliente_direccion = self.cleaned_data.get('cliente_direccion', '')
        factura.cliente_telefono = self.cleaned_data.get('cliente_telefono', '')
        factura.condicion_venta = self.cleaned_data.get('condicion_venta', 'contado')
        
        # Configurar serie por defecto
        factura.establecimiento = "001"
        factura.punto_emision = "001"
        factura.timbrado = self.cleaned_data.get('timbrado', '')
        
        if commit:
            factura.save()
            
        return factura


# Formsets para items dinámicos
class ItemFacturaForm(forms.Form):
    """
    Form para items individuales de la factura
    """
    descripcion = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": _("Descripción del item")
        })
    )
    
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": "1"
        })
    )
    
    precio_unitario = forms.DecimalField(
        max_digits=12,
        decimal_places=0,
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "1000",
            "min": "0"
        })
    )
    # ========== CAMPO DELETE ==========
    DELETE = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(),
        initial=False
    )

# Formsets para servicios e insumos
ItemFacturaFormSet = forms.formset_factory(
    ItemFacturaForm, 
    extra=0, 
    can_delete=True,
)


# Forms específicos para servicios e insumos (manteniendo compatibilidad)
class LineaServicioForm(forms.Form):
    descripcion = forms.CharField(
        label=_("Servicio"),
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "placeholder": _("Descripción del servicio")
        }),
    )
    cantidad = forms.IntegerField(
        label=_("Cant."),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    precio_unitario = forms.DecimalField(
        label=_("Precio unit."),
        min_value=Decimal("0.0"),
        decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )


class LineaInsumoForm(forms.Form):
    descripcion = forms.CharField(
        label=_("Insumo"),
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "placeholder": _("Descripción del insumo")
        }),
    )
    cantidad = forms.IntegerField(
        label=_("Cant."),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    precio_unitario = forms.DecimalField(
        label=_("Precio unit."),
        min_value=Decimal("0.0"),
        decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )


ServicioFormSet = forms.formset_factory(LineaServicioForm, extra=1, can_delete=True)
InsumoFormSet = forms.formset_factory(LineaInsumoForm, extra=1, can_delete=True)
