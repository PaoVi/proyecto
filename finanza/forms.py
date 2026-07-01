# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from django import forms

from .models import (
    Caja,
    MovimientoFinanciero,
    Cobro,
    PagoProveedor,
)


# ==========================================================
# CAJA FORM
# ==========================================================

class CajaForm(forms.ModelForm):

    class Meta:

        model = Caja

        fields = [
            "monto_inicial",
            "observacion",
        ]

        widgets = {

            "monto_inicial": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Monto inicial",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "observacion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observación de apertura de caja",
                }
            ),
        }

    def clean_monto_inicial(self):

        monto = self.cleaned_data.get(
            "monto_inicial"
        )

        if monto is None:

            raise forms.ValidationError(
                "Debe ingresar un monto inicial."
            )

        if monto < 0:

            raise forms.ValidationError(
                "El monto inicial no puede ser negativo."
            )

        return monto

    def clean_observacion(self):

        observacion = self.cleaned_data.get(
            "observacion"
        )

        if observacion:
            observacion = observacion.strip()

        return observacion


# ==========================================================
# MOVIMIENTO FINANCIERO FORM
# ==========================================================

class MovimientoFinancieroForm(
    forms.ModelForm
):

    class Meta:

        model = MovimientoFinanciero

        fields = [

            "tipo",

            "origen",

            "descripcion",

            "monto",
        ]

        widgets = {

            "tipo": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "origen": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "descripcion": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "0.00",
                }
            ),
        }

    def clean_monto(self):

        monto = self.cleaned_data.get(
            "monto"
        )

        if monto is None:

            raise forms.ValidationError(
                "Debe ingresar un monto."
            )

        if monto <= 0:

            raise forms.ValidationError(
                "El monto debe ser mayor a 0."
            )

        return monto

    def clean_descripcion(self):

        descripcion = self.cleaned_data.get(
            "descripcion"
        )

        if not descripcion:

            raise forms.ValidationError(
                "Debe ingresar una descripción."
            )

        descripcion = descripcion.strip()

        if len(descripcion) < 3:

            raise forms.ValidationError(
                "La descripción debe tener al menos 3 caracteres."
            )

        return descripcion
# ==========================================================
# COBRO FORM
# ==========================================================

class CobroForm(forms.ModelForm):

    class Meta:

        model = Cobro

        fields = [
            "monto",
            "observacion",
        ]

        widgets = {

            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "Monto cobrado",
                }
            ),

            "observacion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observación",
                }
            ),
        }

    def clean_monto(self):

        monto = self.cleaned_data.get(
            "monto"
        )

        if monto <= 0:

            raise forms.ValidationError(
                "El monto debe ser mayor a 0."
            )

        return monto


# ==========================================================
# PAGO PROVEEDOR FORM
# ==========================================================

class PagoProveedorForm(forms.ModelForm):

    class Meta:

        model = PagoProveedor

        fields = [
            "monto",
            "observacion",
        ]

        widgets = {

            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "Monto pagado",
                }
            ),

            "observacion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observación",
                }
            ),
        }

    def clean_monto(self):

        monto = self.cleaned_data.get(
            "monto"
        )

        if monto <= 0:

            raise forms.ValidationError(
                "El monto debe ser mayor a 0."
            )

        return monto
