from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Cliente
import calendar, re
from datetime import date
from vehiculo.models import Vehiculo


class FriendlyDateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        # acepta 14032000 y 14/03/2000
        kwargs.setdefault("input_formats", ["%d%m%Y", "%d/%m/%Y"])
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return super().to_python(value)

        raw = str(value).strip()
        digits = re.sub(r"\D+", "", raw)

        # Intentar DDMMYYYY (8 dígitos)
        if digits.isdigit() and len(digits) == 8:
            try:
                day = int(digits[:2])
                month = int(digits[2:4])
                year = int(digits[4:])
            except ValueError:
                raise ValidationError(_("Formato inválido. Use DDMMYYYY, por ejemplo 30/12/1985."))
        else:
            # Probar formatos estándar (YYYY-MM-DD, etc.)
            return super().to_python(raw)

        # Validaciones específicas
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

        try:
            return date(year, month, day)
        except ValueError:
            raise ValidationError(_("Fecha inválida. Use el formato DDMMYYYY."))


class ClienteForm(forms.ModelForm):
    fecha_nacimiento = FriendlyDateField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control datepicker-ddmmyyyy",
            "placeholder": "DDMMYYYY",
            "inputmode": "numeric",
            "autocomplete": "off",
        })
    )
    fecha_constitucion = FriendlyDateField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control datepicker-ddmmyyyy",
            "placeholder": "DDMMYYYY",
            "inputmode": "numeric",
            "autocomplete": "off",
        })
    )

    class Meta:
        model = Cliente
        fields = [
            "tipo_cliente",
            "tipo_documento",
            "numero_documento",
            "nombre",
            "telefono",
            "email",
            "direccion",
            "fecha_nacimiento",
            "fecha_constitucion",
        ]
        widgets = {
            "tipo_cliente": forms.Select(attrs={"class": "form-select"}),
            "tipo_documento": forms.Select(attrs={"class": "form-select"}),
            "numero_documento": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej.: 1234567 o 80012345-1",
            }),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "cliente@gmail.com",
            }),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
        error_messages = {
            "numero_documento": {
                "unique": _("Ya existe un cliente con este documento."),
                "invalid": _("Número de documento inválido."),
            },
            "telefono": {
                "invalid": _("Formato recomendado: +5959xxxxxxx"),
            },
            "email": {
                "invalid": _("Correo inválido."),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["telefono"].required = True
        self.fields["email"].required = True
        self.fields["numero_documento"].required = True
        self.fields["nombre"].required = True
        self.fields["tipo_documento"].required = True
        self.fields["tipo_cliente"].required = True
        self.fields["direccion"].required = True

    def clean_numero_documento(self):
        numero = (self.cleaned_data.get("numero_documento") or "").strip()
        tipo   = self.cleaned_data.get("tipo_documento")

        if tipo == "RUC" and numero and "-" not in numero:
            raise ValidationError(_("El RUC debe incluir guion. Ej.: 80012345-1"))

        # Validar unicidad (excluyendo el propio)
        qs = Cliente.objects.all()
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if numero and qs.filter(numero_documento=numero).exists():
            raise ValidationError(_("Ya existe un cliente con este documento."))

        return numero

    def clean(self):
        cleaned = super().clean()
        tipo  = cleaned.get("tipo_cliente")
        nac   = cleaned.get("fecha_nacimiento")
        const = cleaned.get("fecha_constitucion")

        def field_has_errors(name: str) -> bool:
            return bool(self.errors.get(name))

        if tipo == Cliente.TipoCliente.fisica:
            if not nac:
                if not field_has_errors("fecha_nacimiento"):
                    self.add_error("fecha_nacimiento", _("Este campo es obligatorio."))
            else:
                hoy = date.today()
                if nac > hoy:
                    self.add_error("fecha_nacimiento", _("La fecha de nacimiento no puede ser mayor a la fecha actual."))
                if nac.year < 1900:
                    self.add_error("fecha_nacimiento", _("La fecha de nacimiento es demasiado antigua."))
                edad = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
                if edad < 18:
                    self.add_error("fecha_nacimiento", _("El cliente debe ser mayor de 18 años."))

        elif tipo == Cliente.TipoCliente.juridica:
            if not const:
                if not field_has_errors("fecha_constitucion"):
                    self.add_error("fecha_constitucion", _("Este campo es obligatorio."))
            else:
                hoy = date.today()
                if const > hoy:
                    self.add_error("fecha_constitucion", _("La fecha de constitución no puede ser mayor a la fecha actual."))
                if const.year < 1800:
                    self.add_error("fecha_constitucion", _("La fecha de constitución es demasiado antigua."))

        return cleaned


class ClienteEditarForm(forms.ModelForm):
    fecha_nacimiento = FriendlyDateField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "DDMMYYYY"})
    )
    fecha_constitucion = FriendlyDateField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "DDMMYYYY"})
    )

    class Meta:
        model = Cliente
        fields = [
            "tipo_cliente",
            "tipo_documento",
            "numero_documento",
            "nombre",
            "telefono",
            "email",
            "direccion",
            "fecha_nacimiento",
            "fecha_constitucion",
            "is_active",
        ]
        widgets = {
            "tipo_cliente": forms.Select(attrs={"class": "form-select"}),
            "tipo_documento": forms.Select(attrs={"class": "form-select"}),
            "numero_documento": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        error_messages = {
            "numero_documento": {
                "invalid": _("Número de documento inválido."),
                "unique": _("Ya existe otro cliente con este documento."),
            },
            "telefono": {"invalid": _("Formato recomendado: +5959xxxxxxx")},
            "email": {"invalid": _("Correo inválido.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Requeridos
        self.fields["numero_documento"].required = True
        self.fields["telefono"].required = True
        self.fields["email"].required = True
        self.fields["nombre"].required = True
        self.fields["tipo_documento"].required = True
        self.fields["tipo_cliente"].required = True
        self.fields["direccion"].required = True

        # Forzar formato DDMMYYYY en inicialización
        for field_name in ["fecha_nacimiento", "fecha_constitucion"]:
            val = self.initial.get(field_name)
            if isinstance(val, date):
                self.initial[field_name] = val.strftime("%d%m%Y")

    def clean_numero_documento(self):
        numero = (self.cleaned_data.get("numero_documento") or "").strip().upper()
        tipo = self.cleaned_data.get("tipo_documento")

        # Validar formato según tipo de documento
        if tipo == "RUC":
            if not re.match(r'^[0-9]{5,12}-[0-9]{1}$', numero):
                raise ValidationError(_("Formato inválido para RUC. Ej.: 80012345-1"))
        elif tipo == "CI_PY":
            if not re.match(r'^[0-9]{5,8}$', numero):
                raise ValidationError(_("Formato inválido para cédula. Ej.: 1234567"))
        elif tipo == "PAS":
            if not re.match(r'^[A-Z0-9]{6,12}$', numero):
                raise ValidationError(_("Formato inválido para pasaporte. Ej.: AB123456"))
        elif tipo == "OTRO":
            if not re.match(r'^[A-Za-z0-9\s\-]{3,20}$', numero):
                raise ValidationError(_("Formato inválido para otro documento."))

        # Validar unicidad (excluyendo el propio)
        qs = Cliente.objects.all()
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if numero and qs.filter(numero_documento=numero).exists():
            raise ValidationError(_("Ya existe un cliente con este documento."))

        return numero

    def clean(self):
        cleaned = super().clean()
        tipo  = cleaned.get("tipo_cliente")
        nac   = cleaned.get("fecha_nacimiento")
        const = cleaned.get("fecha_constitucion")

        def field_has_errors(name: str) -> bool:
            return bool(self.errors.get(name))

        if tipo == Cliente.TipoCliente.fisica:
            if not nac:
                if not field_has_errors("fecha_nacimiento"):
                    self.add_error("fecha_nacimiento", _("Este campo es obligatorio."))
            else:
                hoy = date.today()
                if nac > hoy:
                    self.add_error("fecha_nacimiento", _("La fecha de nacimiento no puede ser mayor a la fecha actual."))
                if nac.year < 1900:
                    self.add_error("fecha_nacimiento", _("La fecha de nacimiento es demasiado antigua."))
                edad = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
                if edad < 18:
                    self.add_error("fecha_nacimiento", _("El cliente debe ser mayor de 18 años."))

        elif tipo == Cliente.TipoCliente.juridica:
            if not const:
                if not field_has_errors("fecha_constitucion"):
                    self.add_error("fecha_constitucion", _("Este campo es obligatorio."))
            else:
                hoy = date.today()
                if const > hoy:
                    self.add_error("fecha_constitucion", _("La fecha de constitución no puede ser mayor a la fecha actual."))
                if const.year < 1800:
                    self.add_error("fecha_constitucion", _("La fecha de constitución es demasiado antigua."))

        return cleaned


class ClienteVincularVehiculoForm(forms.Form):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.none(),
        label="Vehículo",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehiculo"].queryset = (
            Vehiculo.objects.filter(estado=True)
            .order_by("marca", "modelo", "nro_chapa")
        )