from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Proveedor
import re


def _compact(s: str) -> str:
    """Quita espacios internos y extremos."""
    return re.sub(r"\s+", "", (s or "").strip())


def _normalize_py_phone(v: str) -> str:
    if not v:
        return v
    raw = _compact(v)
    if raw.startswith("+595"):
        return raw
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("595"):        # 595xxxx...
        return "+" + digits
    if 7 <= len(digits) <= 9:           # 9xxxxx.. (local)
        return "+595" + digits
    return raw


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "ruc",
            "razon_social",
            "nombre_fantasia",
            "telefono",
            "email",
            "ciudad",
            "direccion",
            "contacto_nombre",
            "contacto_telefono",
        ]
        widgets = {
            "ruc": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "80012345-1",
                "autocomplete": "off",
            }),
            "razon_social": forms.TextInput(attrs={"class": "form-control"}),
            "nombre_fantasia": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+5959xxxxxxx",
                "autocomplete": "off",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "proveedor@correo.com",
            }),
            "ciudad": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "contacto_nombre": forms.TextInput(attrs={"class": "form-control"}),
            "contacto_telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+5959xxxxxxx",
                "autocomplete": "off",
            }),
        }
        help_texts = {
            "ruc": _("Formato recomendado: 80012345-1 (con guion)."),
            "telefono": _("Formato recomendado: +5959xxxxxxx."),
            "contacto_telefono": _("Formato recomendado: +5959xxxxxxx."),
        }
        error_messages = {
            "ruc": {
                "unique": _("Ya existe un proveedor con este RUC."),
                "invalid": _("RUC inválido."),
            },
            "telefono": {
                "invalid": _("Formato recomendado: +5959xxxxxxx."),
            },
            "email": {
                "invalid": _("Correo inválido."),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Requeridos 
        self.fields["ruc"].required = True
        self.fields["razon_social"].required = True
        self.fields["telefono"].required = True

        # Opcionales
        self.fields["nombre_fantasia"].required = False
        self.fields["email"].required = False
        self.fields["ciudad"].required = False
        self.fields["direccion"].required = False
        self.fields["contacto_nombre"].required = False
        self.fields["contacto_telefono"].required = False

    def clean_ruc(self):
        ruc = _compact(self.cleaned_data.get("ruc"))
        if ruc and "-" not in ruc:
            raise ValidationError(_("El RUC debe incluir guion. Ej. 80012345-1"))
        return ruc

    def clean_razon_social(self):
        razon_social = self.cleaned_data.get("razon_social", "").strip()
        return razon_social.upper()

    def clean_telefono(self):
        return _normalize_py_phone(self.cleaned_data.get("telefono"))

    def clean_contacto_telefono(self):
        return _normalize_py_phone(self.cleaned_data.get("contacto_telefono"))



class ProveedorEditarForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "ruc",
            "razon_social",
            "nombre_fantasia",
            "telefono",
            "email",
            "ciudad",
            "direccion",
            "contacto_nombre",
            "contacto_telefono",
            "is_active",
        ]
        widgets = {
            "ruc": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "80012345-1",
                "autocomplete": "off",
            }),
            "razon_social": forms.TextInput(attrs={"class": "form-control"}),
            "nombre_fantasia": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+5959xxxxxxx",
                "autocomplete": "off",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "proveedor@correo.com",
            }),
            "ciudad": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "contacto_nombre": forms.TextInput(attrs={"class": "form-control"}),
            "contacto_telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+5959xxxxxxx",
                "autocomplete": "off",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        error_messages = {
            "ruc": {
                "unique": _("Ya existe otro proveedor con este RUC."),
                "invalid": _("RUC inválido."),
            },
            "telefono": {
                "invalid": _("Formato recomendado: +5959xxxxxxx."),
            },
            "email": {"invalid": _("Correo inválido.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Requeridos
        self.fields["ruc"].required = True
        self.fields["razon_social"].required = True
        self.fields["telefono"].required = True

        # Opcionales
        self.fields["nombre_fantasia"].required = False
        self.fields["email"].required = False
        self.fields["ciudad"].required = False
        self.fields["direccion"].required = False
        self.fields["contacto_nombre"].required = False
        self.fields["contacto_telefono"].required = False

    def clean_ruc(self):
        ruc = _compact(self.cleaned_data.get("ruc"))
        if ruc and "-" not in ruc:
            raise ValidationError(_("El RUC debe incluir guion. Ej. 80012345-1"))
        if ruc and Proveedor.objects.filter(ruc=ruc).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("Ya existe otro proveedor con este RUC."))
        return ruc

    def clean_razon_social(self):
        razon_social = self.cleaned_data.get("razon_social", "").strip()
        return razon_social.upper()

    def clean_telefono(self):
        return _normalize_py_phone(self.cleaned_data.get("telefono"))

    def clean_contacto_telefono(self):
        return _normalize_py_phone(self.cleaned_data.get("contacto_telefono"))