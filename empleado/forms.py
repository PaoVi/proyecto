import re
import calendar
from decimal import Decimal, InvalidOperation
from datetime import date
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from .models import Empleado
from seguridad.models import Usuario


# Validadores
telefono_py_validator = RegexValidator(
    regex=r'^\+?595[0-9]{7,9}$',
    message=_("Formato recomendado: +5959xxxxxxx"),
)
cedula_ruc_validator = RegexValidator(
    regex=r'^[0-9]{5,12}(-[0-9]{1})?$',
    message=_("Formato inválido. Ej.: 1234567 o 80012345-1"),
)


class FriendlyDateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", ["%d%m%Y", "%d/%m/%Y", "%Y-%m-%d"])
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return super().to_python(value)

        raw = str(value).strip()
        digits = re.sub(r"\D+", "", raw)

        if digits.isdigit() and len(digits) == 8:
            try:
                day = int(digits[:2])
                month = int(digits[2:4])
                year = int(digits[4:])
            except ValueError:
                raise ValidationError(_("Formato inválido. Use DDMMYYYY, por ejemplo 30/12/1985."))

            if not (1 <= month <= 12):
                raise ValidationError(_("Ingrese un mes válido [01-12]."))

            max_dia_mes = calendar.monthrange(year, month)[1]
            if month == 2 and day == 29 and not calendar.isleap(year):
                raise ValidationError(_("El año %(year)s no es bisiesto; no se permite el 29 de febrero."),
                                      params={"year": year})
            if day > max_dia_mes:
                if month == 2:
                    raise ValidationError(_("Febrero de %(year)s sólo tiene %(max)s días."),
                                          params={"year": year, "max": max_dia_mes})
                elif max_dia_mes == 30:
                    raise ValidationError(_("El mes ingresado solo tiene 30 días."))
                else:
                    raise ValidationError(_("El mes ingresado solo tiene 31 días."))

            try:
                return date(year, month, day)
            except ValueError:
                raise ValidationError(_("Fecha inválida. Use el formato DDMMYYYY."))
        else:
            # Probar formatos estándar
            return super().to_python(raw)


class EmpleadoForm(forms.ModelForm):
    fecha_nacimiento = FriendlyDateField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "dd/mm/aaaa",
            "inputmode": "numeric",
            "autocomplete": "off",
        })
    )
    fecha_ingreso = FriendlyDateField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "dd/mm/aaaa",
            "inputmode": "numeric",
            "autocomplete": "off",
        })
    )

    salario_base = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Gs. 0",
            "inputmode": "numeric",
            "autocomplete": "off",
        })
    )

    class Meta:
        model = Empleado
        fields = [
            "nombre",
            "cedula_ruc",
            "fecha_nacimiento",
            "telefono",
            "direccion",
            "ciudad",
            "correo_electronico",
            "fecha_ingreso",
            "cargo",
            "salario_base",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "cedula_ruc": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej.: 1234567 o 80012345-1",
            }),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "ciudad": forms.TextInput(attrs={"class": "form-control"}),
            "correo_electronico": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "empleado@gmail.com",
            }),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "nombre": _("Nombre"),
            "cedula_ruc": _("Cédula / RUC"),
            "fecha_nacimiento": _("Fecha de Nacimiento"),
            "telefono": _("Teléfono"),
            "direccion": _("Dirección"),
            "ciudad": _("Ciudad"),
            "correo_electronico": _("Correo Electrónico"),
            "fecha_ingreso": _("Fecha de Ingreso"),
            "cargo": _("Cargo"),
            "salario_base": _("Salario Base"),
        }

        error_messages = {
            "cedula_ruc": {"invalid": cedula_ruc_validator.message},
            "telefono": {"invalid": telefono_py_validator.message},
            "correo_electronico": {"invalid": _("Correo inválido.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.required = True

    def clean_cedula_ruc(self):
        value = (self.cleaned_data.get("cedula_ruc") or "").strip()
        if value:
            cedula_ruc_validator(value)
        return value

    def clean_correo_electronico(self):
        value = (self.cleaned_data.get("correo_electronico") or "").strip()
        if value:
            EmailValidator(message=_("Correo inválido."))(value)
        return value

    def clean_telefono(self):
        value = (self.cleaned_data.get("telefono") or "").strip()
        if value:
            # Añadir +595 si no lo trae
            if not value.startswith("+595"):
                value = "+595" + value
            telefono_py_validator(value)
        return value

    def clean_fecha_nacimiento(self):
        f = self.cleaned_data.get("fecha_nacimiento")
        if f:
            hoy = date.today()
            if f > hoy:
                raise ValidationError(_("La fecha de nacimiento no puede ser mayor a la fecha actual."))
            if f.year < 1900:
                raise ValidationError(_("La fecha de nacimiento es demasiado antigua."))
        return f

    def clean_fecha_ingreso(self):
        f = self.cleaned_data.get("fecha_ingreso")
        if f:
            hoy = date.today()
            if f > hoy:
                raise ValidationError(_("La fecha de ingreso no puede ser mayor a la fecha actual."))
            if f.year < 1900:
                raise ValidationError(_("La fecha de ingreso es demasiado antigua."))
            # Coherencia con nacimiento (si está y es válida)
            nac = self.cleaned_data.get("fecha_nacimiento")
            if nac and f < nac:
                raise ValidationError(_("La fecha de ingreso no puede ser anterior a la fecha de nacimiento."))
        return f

    def clean_salario_base(self):
        raw = (self.cleaned_data.get("salario_base") or "").strip()
        if not raw:
            return raw 

        # quitar prefijo y separadores
        cleaned = (
            raw.replace("Gs.", "").replace("Gs", "")
               .replace(".", "").replace(",", "").replace(" ", "")
        )
        if not cleaned.isdigit():
            raise ValidationError(_("Ingrese un monto válido."))
        try:
            val = Decimal(cleaned)
        except InvalidOperation:
            raise ValidationError(_("Ingrese un monto válido."))
        if val < 0:
            raise ValidationError(_("El salario no puede ser negativo."))
        if val == 0:
            raise ValidationError(_("El salario no puede ser 0 Gs."))
        return val

    def save(self, commit=True):
        empleado = super().save(commit=False)
        
        if commit:
            empleado.save()
            
            # SINCRONIZAR CON USUARIO VINCULADO
            if empleado.user:
                usuario = empleado.user
                necesita_guardar = False
                
                # Sincronizar teléfono (Empleado → Usuario)
                if empleado.telefono and empleado.telefono != usuario.telefono:
                    usuario.telefono = empleado.telefono
                    necesita_guardar = True
                
                # Sincronizar email (Empleado → Usuario)
                if empleado.correo_electronico and empleado.correo_electronico != usuario.email:
                    usuario.email = empleado.correo_electronico
                    necesita_guardar = True
                
                if necesita_guardar:
                    usuario.save()
                    print(f"DEBUG: Sincronizado desde formulario Empleado → Usuario")
        
        return empleado

class EmpleadoEditarForm(EmpleadoForm):
    estado = forms.BooleanField(
        required=False,
        label=_("Estado (Activo/Inactivo)"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    class Meta(EmpleadoForm.Meta):
        fields = EmpleadoForm.Meta.fields + ["estado"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.required = (name != "estado")

    def save(self, commit=True):
        empleado = super().save(commit=False)
        
        if commit:
            empleado.save()
            
            # SINCRONIZAR CON USUARIO VINCULADO
            if empleado.user:
                usuario = empleado.user
                necesita_guardar = False
                
                # Sincronizar teléfono (Empleado → Usuario)
                if empleado.telefono and empleado.telefono != usuario.telefono:
                    usuario.telefono = empleado.telefono
                    necesita_guardar = True
                
                # Sincronizar email (Empleado → Usuario)
                if empleado.correo_electronico and empleado.correo_electronico != usuario.email:
                    usuario.email = empleado.correo_electronico
                    necesita_guardar = True
                
                if necesita_guardar:
                    usuario.save()
                    print(f"DEBUG: Sincronizado desde formulario Empleado → Usuario")
        
        return empleado
    
    
class EmpleadoAsignarUsuarioForm(forms.Form):
    user = forms.ModelChoiceField(
        label=_("Seleccionar Usuario"),
        queryset=Usuario.objects.none(),
        required=True,
        empty_label=_("— Seleccione —"),
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={
            "invalid_choice": _("Seleccione una opción válida."),
        },
    )

    def __init__(self, *args, **kwargs):
        self.empleado = kwargs.pop("empleado", None)
        super().__init__(*args, **kwargs)

        # Solo usuarios activos sin empleado asignado (permitiendo el propio)
        qs = Usuario.objects.filter(is_active=True, empleado__isnull=True)
        if self.empleado and self.empleado.user_id:
            qs = Usuario.objects.filter(pk=self.empleado.user_id) | qs

        self.fields["user"].queryset = qs.order_by("username")

    def clean_user(self):
        user = self.cleaned_data.get("user")
        if user and hasattr(user, "empleado") and user.empleado_id and (
            not self.empleado or user.empleado_id != self.empleado.pk
        ):
            raise ValidationError(_("Este usuario ya está vinculado a otro empleado."))
        return user

    def save(self, commit=True):
        """Sincronizar datos al vincular empleado"""
        user = self.cleaned_data["user"]
        empleado = self.empleado
        
        # SINCRONIZACIÓN BIDIRECCIONAL al vincular
        # Si el usuario no tiene email pero el empleado sí, copiar del empleado al usuario
        if not user.email and empleado.correo_electronico:
            user.email = empleado.correo_electronico
        
        # Si el empleado no tiene email pero el usuario sí, copiar del usuario al empleado
        if not empleado.correo_electronico and user.email:
            empleado.correo_electronico = user.email
        
        # Si el usuario no tiene teléfono pero el empleado sí, copiar del empleado al usuario
        if not user.telefono and empleado.telefono:
            user.telefono = empleado.telefono
        
        # Si el empleado no tiene teléfono pero el usuario sí, copiar del usuario al empleado
        if not empleado.telefono and user.telefono:
            empleado.telefono = user.telefono
        
        if commit:
            user.save()
            empleado.user = user
            empleado.save()
            print(f"DEBUG: Sincronizado al vincular - Usuario: {user.email}, Empleado: {empleado.correo_electronico}")
        
        return user