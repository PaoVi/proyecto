from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from seguridad.utils import obtener_configuracion
import re


class ConfigurablePasswordValidator:
    """
    Validador de contraseñas configurable según las opciones en Configuración del Sistema.
    Soporta tres niveles de complejidad: baja, media y alta.
    """

    def validate(self, password, user=None):
        complejidad = obtener_configuracion('password_complejidad', 'media')
        longitud_minima = int(obtener_configuracion('longitud_minima_password', 8))

        # Validar longitud mínima
        if len(password) < longitud_minima:
            raise ValidationError(
                _("La contraseña debe tener al menos %(min_length)d caracteres."),
                code='password_too_short',
                params={'min_length': longitud_minima},
            )

        # Validar complejidad según configuración
        if complejidad == 'media':
            if not any(char.isdigit() for char in password):
                raise ValidationError(
                    _("La contraseña debe contener al menos un número."),
                    code='password_no_number',
                )
            if not any(char.isalpha() for char in password):
                raise ValidationError(
                    _("La contraseña debe contener al menos una letra."),
                    code='password_no_letter',
                )

        elif complejidad == 'alta':
            if not any(char.isdigit() for char in password):
                raise ValidationError(
                    _("La contraseña debe contener al menos un número."),
                    code='password_no_number',
                )
            if not any(char.isupper() for char in password):
                raise ValidationError(
                    _("La contraseña debe contener al menos una letra mayúscula."),
                    code='password_no_upper',
                )
            if not any(char.islower() for char in password):
                raise ValidationError(
                    _("La contraseña debe contener al menos una letra minúscula."),
                    code='password_no_lower',
                )
            if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for char in password):
                raise ValidationError(
                    _("La contraseña debe contener al menos un carácter especial."),
                    code='password_no_special',
                )

    def get_help_text(self):
        """
        Mensaje de ayuda que aparece en los formularios para guiar al usuario
        sobre los requisitos de la contraseña.
        """
        complejidad = obtener_configuracion('password_complejidad', 'media')
        longitud_minima = int(obtener_configuracion('longitud_minima_password', 8))

        help_text = _(f"La contraseña debe tener al menos {longitud_minima} caracteres.")

        if complejidad == 'media':
            help_text += _(" Debe contener al menos una letra y un número.")
        elif complejidad == 'alta':
            help_text += _(" Debe contener al menos una letra mayúscula, una minúscula, un número y un carácter especial.")

        return help_text
