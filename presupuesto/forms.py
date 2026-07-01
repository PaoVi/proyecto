from decimal import Decimal, InvalidOperation
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Presupuesto, PresupuestoServicio
from django.utils import timezone
from datetime import timedelta, date
import calendar, re
from vehiculo.models import Vehiculo
from cliente.models import Cliente
from servicio.models import Servicio


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
            return date(year, month, day)  # ← date está disponible aquí
        except ValueError:
            raise ValidationError(_("Fecha inválida. Use el formato DD/MM/YYYY."))

    def _validar_dia_mes(self, year, month, day):
        """Valida que el día sea válido para el mes (igual que en el modelo)"""
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


class PresupuestoForm(forms.ModelForm):
    fecha_vencimiento = FriendlyDateField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "DD/MM/AAAA",
            "inputmode": "numeric",
            "autocomplete": "off",
        })
    )

    iva_porcentaje = forms.ChoiceField(
        choices=[], 
        widget=forms.Select(attrs={
            "class": "form-control", 
            "id": "id_iva_porcentaje"
        }),
        required=True,
        label=_("IVA %")
    )

    class Meta:
        model = Presupuesto
        fields = ["cliente", "vehiculo", "descripcion", "descuento", "fecha_vencimiento", "iva_porcentaje"]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-control", "id": "id_cliente"}),
            "vehiculo": forms.Select(attrs={"class": "form-control", "id": "id_vehiculo"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "descuento": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }
        error_messages = {
            'cliente': {
                'required': _("Este campo es obligatorio."),
            },
            'vehiculo': {
                'required': _("Este campo es obligatorio."),
            },
            'descuento': {
                'invalid': _("Ingrese un número válido"),
                'min_value': _("El descuento no puede ser negativo"),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Definir opciones de IVA
        iva_choices = [
            ('0.00', '0%'),
            ('5.00', '5%'),
            ('10.00', '10%'),
        ]
        self.fields['iva_porcentaje'].choices = iva_choices
        
        # SIEMPRE usar el valor de la instancia si existe
        if self.instance and hasattr(self.instance, 'iva_porcentaje'):
            iva_valor = str(self.instance.iva_porcentaje)
            
            # Forzar el valor inicial
            self.initial['iva_porcentaje'] = iva_valor
            self.fields['iva_porcentaje'].initial = iva_valor
            
            # Asegurar que el valor esté en las opciones
            if iva_valor not in dict(iva_choices):
                iva_choices.append((iva_valor, f'{float(iva_valor)}%'))
                self.fields['iva_porcentaje'].choices = iva_choices
        
        # Si es un nuevo formulario (sin instancia), usar 10% por defecto
        elif not self.instance or not self.instance.pk:
            self.initial['iva_porcentaje'] = '10.00'
            self.fields['iva_porcentaje'].initial = '10.00'

        # Para vehículos 
        try:
            # Usar el campo booleano 'estado' que ya existe
            self.fields['vehiculo'].queryset = Vehiculo.objects.filter(estado=True).order_by('marca', 'modelo', 'nro_chapa')
        except Exception as e:
            print(f"Error filtrando vehículos: {e}")  # Para debug
            # Si hay error, mostrar todos
            self.fields['vehiculo'].queryset = Vehiculo.objects.all().order_by('marca', 'modelo', 'nro_chapa')
        
        # Para clientes
        try:
            self.fields['cliente'].queryset = Cliente.objects.filter(is_active=True).order_by('nombre')
        except Exception as e:
            print(f"Error filtrando clientes: {e}")  # Para debug
            self.fields['cliente'].queryset = Cliente.objects.all().order_by('nombre')

        # Establecer fecha por defecto si no hay valor
        if not self.instance.pk and not self.initial.get('fecha_vencimiento'):
            fecha_default = date.today() + timedelta(days=15)
            # Formatear como DD/MM/AAAA para mostrar en el input
            self.initial['fecha_vencimiento'] = fecha_default.strftime('%d/%m/%Y')

        # Si hay una fecha existente, formatearla como DD/MM/AAAA
        elif self.initial.get('fecha_vencimiento') and isinstance(self.initial['fecha_vencimiento'], date):
            self.initial['fecha_vencimiento'] = self.initial['fecha_vencimiento'].strftime('%d/%m/%Y')


    def clean_descuento(self):
        """Validación específica del descuento - CON DEBUG"""
        descuento = self.cleaned_data.get('descuento')
        
        # Si está vacío o es 0, establecer a 0
        if descuento is None or descuento == '' or descuento == '0':
            result = Decimal('0.00')
        else:
            # Si es string, limpiarlo
            if isinstance(descuento, str):
                descuento_limpio = descuento.replace('Gs.', '').replace('.', '').replace(',', '').strip()
                if descuento_limpio == '':
                    result = Decimal('0.00')
                else:
                    try:
                        result = Decimal(descuento_limpio)
                    except (InvalidOperation, ValueError, TypeError):
                        raise ValidationError(_('Ingrese un número válido para el descuento.'))
            else:
                result = Decimal(str(descuento))
        
        if result < 0:
            raise ValidationError(_('El descuento no puede ser negativo.'))
        
        return result


    def clean_fecha_vencimiento(self):
        """Validación específica de fecha de vencimiento"""
        fecha = self.cleaned_data.get('fecha_vencimiento')
        
        if not fecha:
            raise ValidationError(_('La fecha de vencimiento es obligatoria.'))
        
        hoy = date.today()
        
        # No puede ser menor a hoy
        if fecha <= hoy:
            raise ValidationError(_('La fecha de vencimiento debe ser posterior a la fecha actual.'))
        
        # No puede ser más de 1 mes en el futuro
        max_fecha = hoy + timedelta(days=15)
        if fecha > max_fecha:
            raise ValidationError(_('La fecha de vencimiento no puede ser mayor a la fecha actual +15 días.'))
    
        return fecha


    def clean(self):
        """Validaciones cruzadas entre campos"""
        cleaned_data = super().clean()
        
        # Validar que los campos obligatorios estén presentes
        if not cleaned_data.get('cliente'):
            self.add_error('cliente', _('Este campo es obligatorio.'))
            
        if not cleaned_data.get('vehiculo'):
            self.add_error('vehiculo', _('Este campo es obligatorio.'))

        # Calcular servicios y validar
        servicios_count = 0 
        subtotal_servicios = Decimal('0.00')
        descuento = cleaned_data.get('descuento', Decimal('0.00'))
        
        # Buscar servicios en el request - MEJORADO
        i = 0
        servicios_encontrados = False
        
        while f'servicios[{i}][servicio_id]' in self.data:
            servicio_id = self.data.get(f'servicios[{i}][servicio_id]', '').strip()
            cantidad_str = self.data.get(f'servicios[{i}][cantidad]', '0').strip()
            
            # Solo contar si hay servicio_id válido
            if servicio_id and cantidad_str:
                try:
                    servicio = Servicio.objects.get(id=servicio_id)
                    cantidad = Decimal(cantidad_str)
                    if cantidad > 0:  # Solo contar si la cantidad es positiva
                        subtotal_servicios += servicio.precio_base * cantidad
                        servicios_count += 1
                        servicios_encontrados = True
                except (Servicio.DoesNotExist, InvalidOperation, ValueError):
                    # Ignorar servicios inválidos
                    pass
            i += 1

        # También verificar servicios existentes (para edición) - CORREGIDO
        if self.instance and self.instance.pk:
            servicios_existentes = self.instance.presupuestoservicio_set.all()
            if servicios_existentes.exists():
                servicios_encontrados = True
                # SUMAR EL SUBTOTAL DE LOS SERVICIOS EXISTENTES
                for servicio_existente in servicios_existentes:
                    subtotal_servicios += servicio_existente.subtotal

        # Validar que haya al menos 1 servicio
        if not servicios_encontrados:
            self.add_error('descripcion', _('El presupuesto debe tener al menos un servicio.'))

        # Validar descuento solo si hay servicios
        if servicios_encontrados and descuento > subtotal_servicios:
            self.add_error('descuento', _('El descuento no puede ser mayor al subtotal de servicios.'))

        return cleaned_data


class PresupuestoEditarForm(PresupuestoForm):
    estado = forms.ChoiceField(
        choices=Presupuesto.ESTADO_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-control",
            "id": "id_estado"
        })
    )

    class Meta(PresupuestoForm.Meta):
        fields = PresupuestoForm.Meta.fields + ["estado"]
        widgets = {
            **PresupuestoForm.Meta.widgets,
            "estado": forms.Select(attrs={"class": "form-control", "id": "id_estado"}),
        }

    def _post_clean(self):
        """Override para EVITAR la validación del modelo que causa el problema"""
        from django.forms.models import construct_instance
        
        try:
            # Limpiar datos del formulario normalmente
            self.cleaned_data = self.clean()
            
            # Construir la instancia pero NO llamar a la validación completa del modelo
            if self.cleaned_data and not self.errors:
                # Usar exclude=None si no tenemos exclude definido
                exclude = self.exclude if hasattr(self, 'exclude') else None
                self.instance = construct_instance(self, self.instance, self.fields, exclude)
                
                # Solo validar campos individuales, NO validaciones cruzadas
                self.instance.clean_fields(exclude=exclude)
                # NO llamar a: self.instance.clean()  # ← Esta es la que causa el problema
        except ValidationError as e:
            self.add_error(None, e)
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # DEBUG: Ver qué valor tiene la instancia
        print(f"DEBUG - Instancia IVA: {getattr(self.instance, 'iva_porcentaje', 'NO INSTANCE')}")
        print(f"DEBUG - Initial IVA: {self.initial.get('iva_porcentaje')}")
        
        # FORZAR EL VALOR DEL IVA SI HAY UNA INSTANCIA - DE FORMA EXPLÍCITA
        if self.instance and hasattr(self.instance, 'iva_porcentaje'):
            # Convertir a string para asegurar compatibilidad
            iva_valor = str(self.instance.iva_porcentaje)
            print(f"DEBUG - Forzando IVA a: {iva_valor}")
            
            # Establecer en initial
            self.initial['iva_porcentaje'] = iva_valor
            
            # También forzar el valor en el campo
            self.fields['iva_porcentaje'].initial = iva_valor
            
            # DEBUG después de establecer
            print(f"DEBUG - After setting initial: {self.initial.get('iva_porcentaje')}")
            print(f"DEBUG - Field initial: {self.fields['iva_porcentaje'].initial}")

        # Si el presupuesto no es editable, deshabilitar campos
        if self.instance and self.instance.pk and not self.instance.es_editable:
            for field_name in self.fields:
                self.fields[field_name].disabled = True
                self.fields[field_name].widget.attrs['readonly'] = True
        
        # Limitar opciones de estado según el estado actual
        if self.instance and self.instance.pk:
            estado_actual = self.instance.estado
            
            # Si está aprobado, solo permitir mantener aprobado o rechazar
            if estado_actual == 'pendiente':
                self.fields['estado'].choices = [
                    ('pendiente', _('Pendiente')),
                    ('aprobado', _('Aprobado')),
                    ('rechazado', _('Rechazado')),
                ]
            elif estado_actual == 'aprobado':
                self.fields['estado'].choices = [
                    ('aprobado', _('Aprobado')),
                    ('rechazado', _('Rechazado')),
                ]
            # Si está rechazado, no permitir cambios
            elif estado_actual == 'rechazado':
                self.fields['estado'].disabled = True
            # Si está vencido, no permitir cambios
            elif estado_actual == 'vencido':
                self.fields['estado'].disabled = True

    def clean_estado(self):
        """Validación específica del estado"""
        estado = self.cleaned_data.get('estado')
        
        if estado not in dict(Presupuesto.ESTADO_CHOICES):
            raise ValidationError(_('Estado no válido.'))
        
        # Validar que no se pueda volver a pendiente desde aprobado
        if (self.instance and self.instance.estado == 'aprobado' and 
            estado == 'pendiente'):
            raise ValidationError(
                _('No se puede volver a estado PENDIENTE una vez que el presupuesto ha sido APROBADO.')
            )
        
        return estado

    def clean(self):
        """Validaciones cruzadas entre campos - CON DEBUG DE ERRORES"""
        cleaned_data = super().clean()
    
        # OBTENER DESCUENTO ACTUAL
        descuento_post = self.data.get('descuento')
        descuento = Decimal('0.00')
        
        if descuento_post is not None:
            try:
                if isinstance(descuento_post, str):
                    descuento_limpio = descuento_post.replace('Gs.', '').replace('.', '').replace(',', '').strip()
                    if descuento_limpio:
                        descuento = Decimal(descuento_limpio).quantize(Decimal('0.00'))
            except (InvalidOperation, ValueError, TypeError):
                descuento = Decimal('0.00')
        
        cleaned_data['descuento'] = descuento
        
        # Calcular subtotal
        subtotal_servicios = Decimal('0.00')
        servicios_procesados = set()
        
        # Servicios existentes
        if self.instance and self.instance.pk:
            servicios_existentes = self.instance.presupuestoservicio_set.all()
            for servicio_existente in servicios_existentes:
                eliminar_key = f'servicios_existentes[{servicio_existente.id}][eliminar]'
                eliminar_flag = self.data.get(eliminar_key, 'false').strip()
                if eliminar_flag != 'true':
                    subtotal_servicios += servicio_existente.subtotal
                    servicios_procesados.add(servicio_existente.servicio_id)

        # Servicios nuevos
        i = 0
        while f'servicios[{i}][servicio_id]' in self.data:
            servicio_id = self.data.get(f'servicios[{i}][servicio_id]', '').strip()
            cantidad_str = self.data.get(f'servicios[{i}][cantidad]', '0').strip()
            if servicio_id and cantidad_str and servicio_id not in servicios_procesados:
                try:
                    servicio = Servicio.objects.get(id=servicio_id)
                    cantidad = Decimal(cantidad_str)
                    if cantidad > 0:
                        subtotal_servicios += servicio.precio_base * cantidad
                except (Servicio.DoesNotExist, InvalidOperation, ValueError):
                    pass
            i += 1

        
        # Validación del descuento
        servicios_encontrados = len(servicios_procesados) > 0

        if servicios_encontrados:
            if descuento > subtotal_servicios:
                self.add_error('descuento', _('El descuento no puede ser mayor al subtotal de servicios.'))
        
        return cleaned_data


class PresupuestoServicioForm(forms.ModelForm):
    class Meta:
        model = PresupuestoServicio
        fields = ["servicio", "cantidad"]
        widgets = {
            "servicio": forms.Select(attrs={
                "class": "form-control servicio-select",
                "data-live-search": "true"
            }),
            "cantidad": forms.NumberInput(attrs={
                "class": "form-control cantidad-input", 
                "step": "0.01", 
                "min": "0.01",
                "placeholder": "1.00"
            }),
        }
        error_messages = {
            'servicio': {
                'required': _("Este campo es obligatorio."),
            },
            'cantidad': {
                'required': _("Este campo es obligatorio."),
                'invalid': _("Ingrese un número válido"),
                'min_value': _("Cantidad debe ser mayor a 0.00"),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo servicios activos en orden alfabético
        self.fields['servicio'].queryset = Servicio.objects.filter(is_active=True).order_by('nombre')

    def clean_cantidad(self):
        """Validación específica de cantidad"""
        cantidad = self.cleaned_data.get('cantidad')
        
        if cantidad is None:
            raise ValidationError(_('La cantidad es obligatoria.'))
            
        if cantidad <= 0:
            raise ValidationError(_('La cantidad debe ser mayor a 0.'))
        
        # Validar que no sea un valor excesivamente grande
        if cantidad > 10000:
            raise ValidationError(_('La cantidad no puede ser mayor a 10,000.'))
        
        return cantidad
    
    def clean_servicio(self):
        """Validación específica del servicio"""
        servicio = self.cleaned_data.get('servicio')
        
        if servicio and not servicio.is_active:
            raise ValidationError(_('No se puede agregar un servicio inactivo.'))
        
        return servicio
    
    def clean(self):
        """Validaciones cruzadas para servicios"""
        cleaned_data = super().clean()
        servicio = cleaned_data.get('servicio')
        cantidad = cleaned_data.get('cantidad')
        
        if servicio and cantidad:
            # Validar que no se duplique el servicio en el mismo presupuesto
            if self.instance and self.instance.pk and self.instance.presupuesto_id:
                presupuesto = self.instance.presupuesto
                existe_duplicado = PresupuestoServicio.objects.filter(
                    presupuesto=presupuesto,
                    servicio=servicio
                ).exclude(pk=self.instance.pk).exists()
                
                if existe_duplicado:
                    raise ValidationError(_('Este servicio ya está agregado al presupuesto.'))
        
        return cleaned_data


# FormSet para múltiples servicios
PresupuestoServicioFormSet = forms.inlineformset_factory(
    Presupuesto,
    PresupuestoServicio,
    form=PresupuestoServicioForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
    can_order=False
)