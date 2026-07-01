# pylint: disable=E1101,no-member,broad-exception-caught
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import re
import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Compra, CompraProducto
from proveedor.models import Proveedor
from insumo.models import Insumo


class FriendlyDateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        # acepta 14032000, 14/03/2000 y 14-03-2000
        kwargs.setdefault("input_formats", ["%d%m%Y", "%d/%m/%Y", "%d-%m-%Y"])
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return super().to_python(value)

        raw = str(value).strip()
        
        # Si ya tiene formato con barras o guiones, usar el método padre
        if '/' in raw or '-' in raw:
            return super().to_python(raw)
            
        digits = re.sub(r"\D+", "", raw)

        # Intentar DDMMYYYY (8 dígitos)
        if digits.isdigit() and len(digits) == 8:
            try:
                day = int(digits[:2])
                month = int(digits[2:4])
                year = int(digits[4:])
            except ValueError:
                raise ValidationError(_("Formato inválido. Use DDMMYYYY, DD/MM/YYYY o DD-MM-YYYY"))
        else:
            # Probar formatos estándar
            return super().to_python(raw)

        # Validaciones específicas de día/mes
        self._validar_dia_mes(year, month, day)

        try:
            return date(year, month, day)
        except ValueError:
            raise ValidationError(_("Fecha inválida. Use el formato DD/MM/YYYY."))

    def _validar_dia_mes(self, year, month, day):
        """Valida que el día sea válido para el mes"""
        # Validar mes
        if not (1 <= month <= 12):
            raise ValidationError(_("Ingrese un mes válido [01-12]."))

        max_dia_mes = calendar.monthrange(year, month)[1]

        # Validar año bisiesto
        if month == 2 and day == 29 and not calendar.isleap(year):
            raise ValidationError(
                _("El año %(year)s no es bisiesto; no se permite el 29 de febrero."),
                params={"year": year}
            )

        # Validar días del mes
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


class CompraForm(forms.ModelForm):
    fecha_entrega_esperada = FriendlyDateField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "DD/MM/AAAA",
            "inputmode": "numeric",
            "autocomplete": "off",
        })
    )

    class Meta:
        model = Compra
        fields = ["proveedor", "descripcion", "fecha_entrega_esperada", "descuento", "iva_porcentaje"]
        widgets = {
            "proveedor": forms.Select(attrs={"class": "form-control", "id": "proveedor-search"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "descuento": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "iva_porcentaje": forms.Select(attrs={"class": "form-control", "id": "id_iva_porcentaje"}),
        }
        error_messages = {
            'proveedor': {
                'required': _("Debe seleccionar un proveedor."),
            },
            'descuento': {
                'invalid': _("Ingrese un número válido"),
                'min_value': _("El descuento no puede ser negativo"),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Opciones de IVA
        iva_choices = [
            ('0.00', '0%'),
            ('5.00', '5%'),
            ('10.00', '10%'),
        ]
        self.fields['iva_porcentaje'].choices = iva_choices
        
        # Valor por defecto
        if not self.instance or not self.instance.pk:
            self.initial['iva_porcentaje'] = '10.00'
            self.initial['descuento'] = '0'
        
        # Proveedores activos
        self.fields['proveedor'].queryset = Proveedor.objects.filter(is_active=True).order_by('razon_social')

    def clean_descuento(self):
        """Validación del descuento"""
        descuento = self.cleaned_data.get('descuento')
        
        if descuento is None or descuento == '':
            return Decimal('0.00')
        
        if isinstance(descuento, str):
            descuento_limpio = descuento.replace('Gs.', '').replace('.', '').replace(',', '').strip()
            if descuento_limpio == '':
                return Decimal('0.00')
            try:
                return Decimal(descuento_limpio)
            except (InvalidOperation, ValueError, TypeError):
                raise ValidationError(_('Ingrese un número válido para el descuento.'))
        
        if descuento < 0:
            raise ValidationError(_('El descuento no puede ser negativo.'))
        
        return descuento

    def clean_fecha_entrega_esperada(self):
        """Validación de fecha de entrega"""
        fecha = self.cleaned_data.get('fecha_entrega_esperada')
        
        if not fecha:
            raise ValidationError(_('La fecha de entrega es obligatoria.'))
        
        hoy = date.today()
        
        # No puede ser menor a hoy
        if fecha < hoy:
            raise ValidationError(_('La fecha de entrega no puede ser menor a la fecha actual.'))
        
        # No puede ser más de 6 meses en el futuro
        max_fecha = hoy + timedelta(days=180)  # 6 meses aprox
        if fecha > max_fecha:
            raise ValidationError(_('La fecha de entrega no puede ser mayor a 6 meses desde hoy.'))
        
        return fecha

    def clean(self):
        """Validaciones cruzadas"""
        cleaned_data = super().clean()
        
        # Validar proveedor
        if not cleaned_data.get('proveedor'):
            self.add_error('proveedor', _('Este campo es obligatorio.'))
        
        # Calcular productos y validar
        productos_count = 0
        subtotal_productos = Decimal('0.00')
        descuento = cleaned_data.get('descuento', Decimal('0.00'))
        
        # Buscar productos en el request
        i = 0
        productos_encontrados = False
        
        while f'productos[{i}][producto_id]' in self.data:
            producto_id = self.data.get(f'productos[{i}][producto_id]', '').strip()
            cantidad_str = self.data.get(f'productos[{i}][cantidad]', '0').strip()
            
            if producto_id and cantidad_str:
                try:
                    producto = Insumo.objects.get(id=producto_id)
                    cantidad = Decimal(cantidad_str)
                    if cantidad > 0:
                        subtotal_productos += producto.costo_unitario * cantidad
                        productos_count += 1
                        productos_encontrados = True
                except (Insumo.DoesNotExist, InvalidOperation, ValueError):
                    pass
            i += 1
        
        # También verificar productos existentes (para edición)
        if self.instance and self.instance.pk:
            productos_existentes = self.instance.detalles.all()
            if productos_existentes.exists():
                productos_encontrados = True
        
        # Validar que haya al menos 1 producto
        if not productos_encontrados:
            self.add_error('descripcion', _('La orden de compra debe tener al menos un producto.'))
        
        # Validar descuento
        if productos_encontrados and descuento > subtotal_productos:
            self.add_error('descuento', _('El descuento no puede ser mayor al subtotal de productos.'))
        
        return cleaned_data


class CompraEditarForm(CompraForm):
    estado = forms.ChoiceField(
        choices=Compra.ESTADO_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-control",
            "id": "id_estado"
        }),
        required=False
    )

    class Meta(CompraForm.Meta):
        fields = CompraForm.Meta.fields + ["estado"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hacer que proveedor NO sea requerido en edición
        if self.instance and self.instance.pk:
            self.fields['proveedor'].required = False
            self.fields['proveedor'].widget.attrs['disabled'] = 'disabled'
            # También eliminar la validación del proveedor en el clean
            self.fields['proveedor'].error_messages = {}
            self.fields['proveedor'].validators = []
        
        # Si la compra no es editable, deshabilitar campos
        if self.instance and self.instance.pk and not self.instance.es_editable:
            for field_name in self.fields:
                self.fields[field_name].disabled = True

    # ======================================================
    # SOBRESCRIBIR CLEAN PARA EVITAR VALIDAR PROVEEDOR
    # ======================================================
    def clean(self):
        # NO llamar a super().clean() para evitar la validación del proveedor
        cleaned_data = self.cleaned_data
        
        # Validar solo si es creación (sin instancia)
        if not self.instance or not self.instance.pk:
            # Validar proveedor solo en creación
            if not cleaned_data.get('proveedor'):
                self.add_error('proveedor', _('Este campo es obligatorio.'))
        
        # Validar fecha de entrega
        fecha = cleaned_data.get('fecha_entrega_esperada')
        if fecha:
            hoy = date.today()
            if fecha < hoy:
                self.add_error('fecha_entrega_esperada', _('La fecha de entrega no puede ser menor a la fecha actual.'))
            max_fecha = hoy + timedelta(days=180)
            if fecha > max_fecha:
                self.add_error('fecha_entrega_esperada', _('La fecha de entrega no puede ser mayor a 6 meses desde hoy.'))
        
        # Calcular productos y validar (solo para creación)
        if not self.instance or not self.instance.pk:
            i = 0
            productos_encontrados = False
            subtotal_productos = Decimal('0.00')
            descuento = cleaned_data.get('descuento', Decimal('0.00'))
            
            while f'productos[{i}][producto_id]' in self.data:
                producto_id = self.data.get(f'productos[{i}][producto_id]', '').strip()
                cantidad_str = self.data.get(f'productos[{i}][cantidad]', '0').strip()
                
                if producto_id and cantidad_str:
                    try:
                        producto = Insumo.objects.get(id=producto_id)
                        cantidad = Decimal(cantidad_str)
                        if cantidad > 0:
                            subtotal_productos += producto.costo_unitario * cantidad
                            productos_encontrados = True
                    except (Insumo.DoesNotExist, InvalidOperation, ValueError):
                        pass
                i += 1
            
            if not productos_encontrados:
                self.add_error('descripcion', _('La orden de compra debe tener al menos un producto.'))
            
            if productos_encontrados and descuento > subtotal_productos:
                self.add_error('descuento', _('El descuento no puede ser mayor al subtotal de productos.'))
        
        return cleaned_data

    # ======================================================
    # DESCUENTO
    # ======================================================

    def clean_descuento(self):

        desc = self.cleaned_data.get(
            "descuento"
        )

        if not desc:

            return Decimal("0.00")

        if isinstance(desc, str):

            desc = (
                desc.replace("Gs.", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )

        try:

            desc = Decimal(str(desc))

        except (
            ValueError,
            TypeError
        ) as exc:

            raise ValidationError(
                _("Ingrese un descuento válido.")
            ) from exc

        if desc < 0:

            raise ValidationError(
                _("El descuento no puede ser negativo.")
            )

        return desc

    # ======================================================
    # VALIDACION GENERAL (SIN VALIDAR PROVEEDOR)
    # ======================================================

    def clean(self):

        cleaned_data = super().clean()

        descuento = cleaned_data.get(
            "descuento",
            Decimal("0.00")
        )

        descuento = descuento or Decimal("0.00")

        # Calcular subtotal de productos actuales de la compra
        subtotal = Decimal("0.00")

        if self.instance and self.instance.pk:
            for detalle in self.instance.detalles.all():
                subtotal += detalle.subtotal

        # Agregar productos nuevos si los hay
        i = 0
        while f"productos_nuevos[{i}][producto_id]" in self.data:
            producto_id = self.data.get(f"productos_nuevos[{i}][producto_id]", "").strip()
            cantidad_str = self.data.get(f"productos_nuevos[{i}][cantidad]", "0").strip()

            if producto_id and cantidad_str:
                try:
                    cantidad = Decimal(cantidad_str)
                    if cantidad > 0:
                        producto = Insumo.objects.get(id=producto_id)
                        precio = getattr(producto, "costo_unitario", None) or Decimal("0.00")
                        subtotal += precio * cantidad
                except (ValueError, Insumo.DoesNotExist):
                    pass
            i += 1

        # Validar descuento
        if subtotal > 0 and descuento > subtotal:
            self.add_error(
                "descuento",
                _("El descuento no puede superar el subtotal de productos.")
            )

        return cleaned_data


# ==========================================================
# DETALLE PRODUCTOS
# ==========================================================

class CompraProductoForm(forms.Form):

    producto = forms.ModelChoiceField(

        queryset=Insumo.objects.all().order_by(
            "nombre"
        ),

        widget=forms.Select(
            attrs={
                "class": "form-control select2",
            }
        ),
    )

    cantidad = forms.DecimalField(

        min_value=Decimal("0.01"),

        decimal_places=2,

        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "0.01",
            }
        ),
    )


# ==========================================================
# FORMSET
# ==========================================================

CompraProductoFormSet = forms.formset_factory(

    CompraProductoForm,

    extra=1,

    can_delete=True,
)