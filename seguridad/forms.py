import re
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, Permission
from .models import ConfiguracionSistema, Usuario, obtener_permisos_personalizados
from seguridad.validators import ConfigurablePasswordValidator
from empleado.models import Empleado


# ========
# USUARIOS
# ========
class UsuarioForm(UserCreationForm):
    error_messages = {
        **getattr(UserCreationForm, "error_messages", {}),
        "password_mismatch": _("Las contraseñas no coinciden."),
    }

    class Meta:
        model = Usuario
        fields = ['username', 'password1', 'password2', 'rol']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-control'})
        }
        error_messages = {
            'username': {'unique': _("Ya existe un usuario con ese nombre.")},
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Etiquetas/ayudas
        self.fields['username'].label = _("Usuario")
        self.fields['password1'].label = _("Contraseña")
        self.fields['password2'].label = _("Confirmar contraseña")
        self.fields['password1'].help_text = _("Mínimo 8 caracteres y al menos 1 número.")
        self.fields['password2'].help_text = _("Repita la contraseña anterior.")

        # Obtener roles disponibles dinámicamente - SOLO ACTIVOS
        roles_disponibles = Usuario.obtener_todos_los_roles()

        # Filtrar solo grupos activos
        grupos_activos = Group.objects.filter(activo=True)
        roles_filtrados = []

        for codigo, nombre in roles_disponibles:
            if codigo in ['admin', 'mecanico', 'chapista', 'recepcion']:
                mapeo_rol_a_grupo = {
                    'admin': 'Administrador',
                    'mecanico': 'Mecánico',
                    'chapista': 'Chapista',
                    'recepcion': 'Recepcionista'
                }
                nombre_grupo = mapeo_rol_a_grupo.get(codigo, nombre)
                if grupos_activos.filter(name=nombre_grupo).exists():
                    roles_filtrados.append((codigo, nombre))
            else:
                if grupos_activos.filter(name=nombre).exists():
                    roles_filtrados.append((codigo, nombre))

        # Choices (Django validará "required" si queda en blanco)
        self.fields['rol'].choices = [('', _('Seleccionar rol'))] + roles_filtrados

        # Añadir clase a widgets
        for field in self.fields.values():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                field.widget.attrs['class'] = 'form-control'

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        if rol:
            roles_disponibles = [codigo for codigo, _ in self.fields['rol'].choices if codigo]
            if rol not in roles_disponibles:
                raise ValidationError(_("El rol seleccionado no está disponible."))
        return rol

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError(_('Este nombre de usuario ya existe. Por favor, elige otro.'))
        return username

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            validator = ConfigurablePasswordValidator()
            try:
                validator.validate(password)
            except ValidationError as e:
                raise ValidationError([_(m) for m in e.messages])
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(_("Las contraseñas no coinciden."))

        return password2


class UsuarioEditarForm(forms.ModelForm):
    nueva_contraseña = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Dejar vacío para mantener la contraseña actual')
        }),
        label=_("Nueva Contraseña"),
        help_text=_("Mínimo 8 caracteres y al menos 1 número."),
    )

    is_active = forms.BooleanField(
        required=False,
        label=_("Estado"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Usuario
        fields = ['username', 'rol', 'is_active']
        labels = {
            'username': _('Usuario'),
            'rol': _('Rol'),
            'is_active': _('Estado'),
        }
        error_messages = {
            'username': {'unique': _("Ya existe un usuario con ese nombre.")},
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.request = kwargs.pop('request', None)  
        super().__init__(*args, **kwargs)

        # Si el usuario está editándose a sí mismo, no permitir cambiar el estado
        if self.instance and self.instance.pk == self.user.pk:
            self.fields['is_active'].disabled = True
            self.fields['is_active'].help_text = _("No puedes cambiar tu propio estado.")

        roles_disponibles = Usuario.obtener_todos_los_roles()
        grupos_activos = Group.objects.filter(activo=True)
        roles_filtrados = []

        for codigo, nombre in roles_disponibles:
            if codigo in ['admin', 'mecanico', 'chapista', 'recepcion']:
                mapeo_rol_a_grupo = {
                    'admin': 'Administrador',
                    'mecanico': 'Mecánico',
                    'chapista': 'Chapista',
                    'recepcion': 'Recepcionista'
                }
                nombre_grupo = mapeo_rol_a_grupo.get(codigo, nombre)
                if grupos_activos.filter(name=nombre_grupo).exists():
                    roles_filtrados.append((codigo, nombre))
            else:
                if grupos_activos.filter(name=nombre).exists():
                    roles_filtrados.append((codigo, nombre))

        self.fields['rol'].choices = [('', _('Seleccionar rol'))] + roles_filtrados

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')

        if rol:
            roles_disponibles = [codigo for codigo, _ in self.fields['rol'].choices if codigo]
            if rol not in roles_disponibles:
                raise ValidationError(_("El rol seleccionado no está disponible."))
        return rol

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # Validar que no esté vacío
        if not username:
            raise ValidationError(_("El nombre de usuario es obligatorio."))
            
        if username and Usuario.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Este nombre de usuario ya existe. Por favor, elige otro.'))
        return username
    
    def clean_nueva_contraseña(self):
        password = self.cleaned_data.get('nueva_contraseña')
        if password:
            validator = ConfigurablePasswordValidator()
            try:
                validator.validate(password)
            except ValidationError as e:
                raise ValidationError([_(m) for m in e.messages])
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('nueva_contraseña')
        es_propio_usuario = user.pk == self.user.pk

        # SINCRONIZACIÓN CON EMPLEADO VINCULADO
        try:
            empleado_vinculado = None
            try:
                empleado_vinculado = Empleado.objects.get(user=user)
                print(f"DEBUG: Sincronizando con empleado {empleado_vinculado.nombre}")
            except Empleado.DoesNotExist:
                pass
        except Exception as e:
            print(f"DEBUG: Error en sincronización: {e}")

        # Cambiar contraseña si se proporcionó una nueva
        if password and password.strip():
            user.set_password(password)
            print(f"DEBUG: Contraseña cambiada para usuario {user.username}")

        # Siempre guardar el usuario
        if commit:
            user.save()
            print(f"DEBUG: Usuario guardado - Cambio contraseña: {bool(password)}")
            
            # Mantener sesión solo si es el propio usuario y cambió contraseña
            if es_propio_usuario and password and self.request:
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(self.request, user)
                print(f"DEBUG: Sesión mantenida después de cambio de contraseña")

            user.asignar_grupo_por_rol()

        return user


class UsuarioAsignarEmpleadoForm(forms.Form):
    empleado = forms.ModelChoiceField(
        label=_("Seleccionar Empleado"),
        queryset=Empleado.objects.none(),
        required=True,
        empty_label=_("— Seleccione —"),
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"invalid_choice": _("Seleccione una opción válida.")},
    )

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        super().__init__(*args, **kwargs)
        qs = Empleado.objects.all()
        qs = qs.filter(user__isnull=True) | qs.filter(user=self.usuario)
        self.fields["empleado"].queryset = qs.order_by("nombre")

    def clean_empleado(self):
        emp = self.cleaned_data["empleado"]
        # Bloquear si ya está vinculado con otro usuario distinto
        if emp.user_id and (not self.usuario or emp.user_id != self.usuario.id):
            raise ValidationError(_("Este empleado ya está vinculado a un usuario."))
        return emp

    def save(self, commit=True):
        """Sincronizar datos al vincular empleado"""
        empleado = self.cleaned_data["empleado"]
        usuario = self.usuario
        
        # SINCRONIZACIÓN BIDIRECCIONAL al vincular
        # Si el usuario no tiene teléfono pero el empleado sí, copiar del empleado al usuario
        if not usuario.telefono and empleado.telefono:
            usuario.telefono = empleado.telefono
        
        # Si el empleado no tiene teléfono pero el usuario sí, copiar del usuario al empleado
        if not empleado.telefono and usuario.telefono:
            empleado.telefono = usuario.telefono
        
        # Sincronizar email también
        if not usuario.email and empleado.correo_electronico:
            usuario.email = empleado.correo_electronico
        
        if not empleado.correo_electronico and usuario.email:
            empleado.correo_electronico = usuario.email
        
        if commit:
            usuario.save()
            empleado.user = usuario
            empleado.save()
            print(f"DEBUG: Sincronizado al vincular - Usuario: {usuario.telefono}, Empleado: {empleado.telefono}")
        
        return empleado
    
# ================
# ROLES Y PERMISOS
# ================
class RolPermisosForm(forms.ModelForm):
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label=_("Permisos del Sistema")
    )

    activo = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Estado (Activo/Inactivo)"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Group
        fields = ['name', 'activo', 'permisos']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Nombre del rol')}
            ),
        }
        error_messages = {
            'name': {
                'unique': _("Ya existe un rol con ese nombre."),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        permisos_permitidos = obtener_permisos_personalizados()

        self.fields['permisos'].queryset = Permission.objects.filter(
            content_type__app_label='seguridad',
            codename__in=permisos_permitidos
        ).order_by('name')

        if self.instance and self.instance.pk:
            self.fields['permisos'].initial = self.instance.permissions.filter(
                content_type__app_label='seguridad',
                codename__in=permisos_permitidos
            )

        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'


    def save(self, commit=True):
        group = super().save(commit=commit)

        perms = self.cleaned_data.get('permisos') or []

        if commit:
            group.permissions.set(perms)
        else:
            def _sync():
                group.permissions.set(perms)
            orig_save_m2m = getattr(self, 'save_m2m', lambda: None)
            def chained_save_m2m():
                orig_save_m2m()
                _sync()
            self.save_m2m = chained_save_m2m

        return group


# =====================
# PERFILES DE USUARIOS
# ====================
class PerfilUsuarioForm(forms.ModelForm):
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-sm password-field',
            'placeholder': _('Contraseña actual (requerida para cambios)'),
            'autocomplete': 'current-password'
        }),
        label=_("Contraseña Actual"),
        help_text=_("Requerida solo si desea cambiar su contraseña.")
    )

    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-sm password-field',
            'placeholder': _('Nueva contraseña (dejar vacío para no cambiar)'),
            'autocomplete': 'new-password'
        }),
        label=_("Nueva Contraseña"),
        min_length=8,
        help_text=_("Mínimo 8 caracteres. Dejar vacío para no cambiar."),
        error_messages={
            'min_length': _("La nueva contraseña debe tener al menos 8 caracteres y 1 número."),
        }
    )

    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-sm password-field',
            'placeholder': _('Confirmar nueva contraseña'),
            'autocomplete': 'new-password'
        }),
        label=_("Confirmar Contraseña")
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'telefono']  
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': _('Nombre de usuario'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': _('Correo electrónico'),
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': _('+5959XXXXXXX'),
            })
        }
        labels = {
            'username': _('Nombre de usuario'),
            'email': _('Correo electrónico'),
            'telefono': _('Teléfono'),
        }
        error_messages = {
            'username': {'unique': _("Ya existe un usuario con ese nombre.")},
            'email': {
                'invalid': _("Ingrese un correo electrónico válido."),
                'unique': _("Ya existe un usuario con ese correo electrónico."),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = True
        
        # Hacer email y teléfono opcionales si el usuario no tiene empleado vinculado
        if self.instance and not hasattr(self.instance, 'empleado'):
            self.fields['email'].required = False
            self.fields['telefono'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        current_password = cleaned_data.get('current_password')

        if new_password:
            if new_password != confirm_password:
                raise ValidationError(_("Las nuevas contraseñas no coinciden."))
            if not current_password:
                raise ValidationError(_("Debe ingresar su contraseña actual para cambiar la contraseña."))
            if not self.instance.check_password(current_password):
                raise ValidationError(_("La contraseña actual es incorrecta."))
        elif current_password and not new_password:
            raise ValidationError(_("Si ingresa su contraseña actual, debe proporcionar una nueva contraseña."))
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and Usuario.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Este nombre de usuario ya existe. Por favor, elige otro.'))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # Solo validar si no está vacío y el usuario tiene empleado vinculado
        if email and hasattr(self.instance, 'empleado') and self.instance.empleado:
            if Usuario.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError(_('Ya existe un usuario con ese correo electrónico.'))
        
        # Si está vacío y el usuario no tiene empleado, permitir
        if not email and not hasattr(self.instance, 'empleado'):
            return email
            
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        
        # Si está vacío y el usuario no tiene empleado, permitir
        if not telefono and not hasattr(self.instance, 'empleado'):
            return telefono
        
        # Si es string, hacer strip
        if isinstance(telefono, str):
            telefono = telefono.strip()
            if not telefono and not hasattr(self.instance, 'empleado'):
                return telefono
        
        # Solo validar formato si hay valor
        if telefono:
            # Normalizar el formato
            if telefono.startswith('595'):
                telefono = '+' + telefono
            elif telefono.startswith('09'):
                telefono = '+595' + telefono[1:]
            elif telefono.startswith('9'):
                telefono = '+595' + telefono
            
            # Validar formato básico
            if not re.match(r'^\+?595[0-9]{7,9}$', telefono):
                raise ValidationError(_("Formato recomendado: +5959XXXXXXX"))
        
        return telefono

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            validator = ConfigurablePasswordValidator()
            try:
                validator.validate(password)
            except ValidationError as e:
                raise ValidationError([_(m) for m in e.messages])
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        
        # SINCRONIZACIÓN CON EMPLEADO VINCULADO
        try:
            # Verificar si el usuario tiene un empleado vinculado
            if hasattr(user, 'empleado') and user.empleado:
                empleado = user.empleado
                
                # Sincronizar EMAIL
                nuevo_email = self.cleaned_data.get('email')
                if nuevo_email:
                    empleado.correo_electronico = nuevo_email
                
                # Sincronizar TELÉFONO
                nuevo_telefono = self.cleaned_data.get('telefono')
                if nuevo_telefono:
                    empleado.telefono = nuevo_telefono
                
                if commit:
                    empleado.save()
                    print(f"DEBUG: Sincronizado - Email: {nuevo_email}, Teléfono: {nuevo_telefono}")
            
        except Exception as e:
            print(f"DEBUG: Error en sincronización: {e}")
        
        if new_password:
            user.set_password(new_password)
        
        if commit:
            user.save()
        
        return user


# ===========================
# CONFIGURACIONES DEL SISTEMA
# ===========================
class ConfiguracionForm(forms.ModelForm):
    grupoConfig = forms.CharField(
        label=_("Grupo"),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text=_("Solo letras minúsculas, números y guiones bajos. Debe empezar con letra.")
    ) 

    class Meta:
        model = ConfiguracionSistema
        fields = ['clave', 'valor', 'tipo', 'descripcion', 'editable']
        widgets = {
            'clave': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'editable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'clave': _('Clave'),
            'valor': _('Valor'),
            'tipo': _('Tipo'),
            'descripcion': _('Descripción'),
            'editable': _('Editable'),
        }
        error_messages = {
            'clave': {'unique': _("Ya existe una configuración con esa clave.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['grupoConfig'].initial = self.instance.grupo

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.grupo = self.cleaned_data.get('grupoConfig')
        if commit:
            instance.save()
        return instance
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def clean_grupoConfig(self):
        grupo = self.cleaned_data.get('grupoConfig')
        if grupo and not re.fullmatch(r'^[a-z][a-z0-9_]*$', grupo):
            raise ValidationError(
                _('El grupo debe contener solo letras minúsculas, números y guiones bajos.')
            )
        return grupo

    def clean_clave(self):
        clave = self.cleaned_data.get('clave')
        if clave and not re.fullmatch(r'^[a-z][a-z0-9_]*$', clave):
            raise ValidationError(
                _('La clave debe contener solo letras minúsculas, números y guiones bajos.')
            )
        return clave


class ConfiguracionEditarForm(ConfiguracionForm):
    grupoConfig = forms.ChoiceField(
        label=_("Grupo de Configuración"),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_("Seleccione un grupo de configuración existente"),
    )

    activo = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Estado (Activo/Inactivo)"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta(ConfiguracionForm.Meta):
        fields = ConfiguracionForm.Meta.fields + ['activo']
        widgets = {
            **ConfiguracionForm.Meta.widgets,
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            **ConfiguracionForm.Meta.labels,
            'activo': _('Activo'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        grupos = ConfiguracionSistema.objects.values_list('grupo', flat=True).distinct().order_by('grupo')
        self.fields['grupoConfig'].choices = [(g, g) for g in grupos if g]

        if self.instance and self.instance.pk:
            self.fields['grupoConfig'].initial = self.instance.grupo

    def save(self, commit=True):
        instance = super().save(commit=False)
        grupo_valor = self.cleaned_data.get("grupoConfig")
        if grupo_valor:
            instance.grupo = grupo_valor
        if commit:
            instance.save()
        return instance


class ConfiguracionBusquedaForm(forms.Form):
    grupo = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_("Grupo")
    )
    clave = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Buscar por clave')
        }),
        label=_("Clave")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        grupos = ConfiguracionSistema.objects.values_list('grupo', flat=True).distinct().order_by('grupo')
        self.fields['grupo'].choices = [('', _('Todos los grupos'))] + [(g, g) for g in grupos if g]


# ==============
# NOTIFICACIONES
# ==============
class EmailNotificacionesForm(forms.Form):
    email_notificaciones = forms.EmailField(
        label="Correo remitente (From)",
        help_text="Se usará como remitente visible de las notificaciones.",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    activo = forms.BooleanField(
        label="Activo",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
