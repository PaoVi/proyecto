from django.core.management.base import BaseCommand
from proveedor.models import Proveedor

class Command(BaseCommand):
    help = 'Carga proveedores iniciales para el taller Iam Car'

    def handle(self, *args, **options):
        proveedores = [
            # ==================== REPUESTOS Y AUTOPARTES ====================
            {
                'ruc': '80012345-1',
                'razon_social': 'AUTOPARTES DEL PARAGUAY S.A.',
                'nombre_fantasia': 'Autoparts PY',
                'telefono': '+59521234567',
                'email': 'ventas@autopartspy.com.py',
                'ciudad': 'Asunción',
                'direccion': 'Av. España 1234, Asunción',
                'contacto_nombre': 'Carlos Martínez',
                'contacto_telefono': '+595981234567',
                'is_active': True
            },
            {
                'ruc': '80023456-2',
                'razon_social': 'IMPORTADORA DE REPUESTOS S.R.L.',
                'nombre_fantasia': 'Import Repuestos',
                'telefono': '+59521245678',
                'email': 'compras@importrepuestos.com.py',
                'ciudad': 'San Lorenzo',
                'direccion': 'Ruta 1 Km 12, San Lorenzo',
                'contacto_nombre': 'María González',
                'contacto_telefono': '+595982345678',
                'is_active': True
            },
            {
                'ruc': '80034567-3',
                'razon_social': 'DISTRIBUIDORA DE FILTROS S.A.',
                'nombre_fantasia': 'Filtros Premium',
                'telefono': '+59521256789',
                'email': 'info@filtrospremium.com.py',
                'ciudad': 'Fernando de la Mora',
                'direccion': 'Av. Mariscal López 567, Fernando de la Mora',
                'contacto_nombre': 'Roberto Benítez',
                'contacto_telefono': '+595983456789',
                'is_active': True
            },
            {
                'ruc': '80045678-4',
                'razon_social': 'FRENOS Y EMBRAGUES S.A.',
                'nombre_fantasia': 'Frenos Seguros',
                'telefono': '+59521267890',
                'email': 'contacto@frenosseguros.com.py',
                'ciudad': 'Lambaré',
                'direccion': 'Av. Brasilia 890, Lambaré',
                'contacto_nombre': 'Diego Silva',
                'contacto_telefono': '+595984567890',
                'is_active': True
            },

            # ==================== LUBRICANTES Y FLUIDOS ====================
            {
                'ruc': '80056789-5',
                'razon_social': 'LUBRICANTES NACIONALES S.A.',
                'nombre_fantasia': 'LubriNacional',
                'telefono': '+59521278901',
                'email': 'pedidos@lubrinacional.com.py',
                'ciudad': 'Asunción',
                'direccion': 'Av. Artigas 345, Asunción',
                'contacto_nombre': 'Ana Vargas',
                'contacto_telefono': '+595985678901',
                'is_active': True
            },
            {
                'ruc': '80067890-6',
                'razon_social': 'FLUIDOS AUTOMOTRICES S.R.L.',
                'nombre_fantasia': 'Fluidos PY',
                'telefono': '+59521289012',
                'email': 'ventas@fluidospy.com.py',
                'ciudad': 'Luque',
                'direccion': 'Calle Aeropuerto 234, Luque',
                'contacto_nombre': 'Luis Fernández',
                'contacto_telefono': '+595986789012',
                'is_active': True
            },

            # ==================== HERRAMIENTAS Y EQUIPOS ====================
            {
                'ruc': '80078901-7',
                'razon_social': 'HERRAMIENTAS PROFESIONALES S.A.',
                'nombre_fantasia': 'HerraPro',
                'telefono': '+59521290123',
                'email': 'cotizaciones@herrapro.com.py',
                'ciudad': 'Asunción',
                'direccion': 'Av. República Argentina 678, Asunción',
                'contacto_nombre': 'Jorge Rojas',
                'contacto_telefono': '+595987890123',
                'is_active': True
            },
            {
                'ruc': '80089012-8',
                'razon_social': 'EQUIPOS DE DIAGNÓSTICO S.R.L.',
                'nombre_fantasia': 'Diagnóstico Rápido',
                'telefono': '+59521301234',
                'email': 'soporte@diagnosticorapido.com.py',
                'ciudad': 'San Lorenzo',
                'direccion': 'Ruta 2 Km 8, San Lorenzo',
                'contacto_nombre': 'Sofía Acosta',
                'contacto_telefono': '+595988901234',
                'is_active': True
            },

            # ==================== NEUMÁTICOS Y LLANTAS ====================
            {
                'ruc': '80090123-9',
                'razon_social': 'NEUMÁTICOS PREMIUM S.A.',
                'nombre_fantasia': 'Neumáticos PY',
                'telefono': '+59521312345',
                'email': 'comercial@neumaticospy.com.py',
                'ciudad': 'Fernando de la Mora',
                'direccion': 'Av. Fernando de la Mora 901, Fernando de la Mora',
                'contacto_nombre': 'Miguel Torres',
                'contacto_telefono': '+595989012345',
                'is_active': True
            },
            {
                'ruc': '80101234-0',
                'razon_social': 'LLANTAS Y ACCESORIOS S.R.L.',
                'nombre_fantasia': 'Llantas Center',
                'telefono': '+59521323456',
                'email': 'info@llantascenter.com.py',
                'ciudad': 'Capiatá',
                'direccion': 'Ruta 2 Km 15, Capiatá',
                'contacto_nombre': 'Patricia Romero',
                'contacto_telefono': '+595981112233',
                'is_active': True
            },

            # ==================== BATERÍAS Y ELÉCTRICOS ====================
            {
                'ruc': '80112345-1',
                'razon_social': 'BATERÍAS AUTOMOTRICES S.A.',
                'nombre_fantasia': 'Baterías Power',
                'telefono': '+59521334567',
                'email': 'ventas@bateriaspower.com.py',
                'ciudad': 'Asunción',
                'direccion': 'Av. Carlos Antonio López 123, Asunción',
                'contacto_nombre': 'Ricardo Díaz',
                'contacto_telefono': '+595982223344',
                'is_active': True
            },
            {
                'ruc': '80123456-2',
                'razon_social': 'SISTEMAS ELÉCTRICOS S.R.L.',
                'nombre_fantasia': 'Eléctrica Total',
                'telefono': '+59521345678',
                'email': 'contacto@electricatotal.com.py',
                'ciudad': 'Ñemby',
                'direccion': 'Calle Principal 456, Ñemby',
                'contacto_nombre': 'Laura Castro',
                'contacto_telefono': '+595983334455',
                'is_active': True
            },

            # ==================== CARROCERÍA Y PINTURA ====================
            {
                'ruc': '80134567-3',
                'razon_social': 'PINTURAS AUTOMOTRICES S.A.',
                'nombre_fantasia': 'Pinturas Pro',
                'telefono': '+59521356789',
                'email': 'color@pinturaspro.com.py',
                'ciudad': 'Asunción',
                'direccion': 'Av. Santísima Trinidad 789, Asunción',
                'contacto_nombre': 'Fernando Morales',
                'contacto_telefono': '+595984445566',
                'is_active': True
            },
            {
                'ruc': '80145678-4',
                'razon_social': 'CARROCERÍA Y ACCESORIOS S.R.L.',
                'nombre_fantasia': 'Carrocería Express',
                'telefono': '+59521367890',
                'email': 'servicio@carroceriaexpress.com.py',
                'ciudad': 'Lambaré',
                'direccion': 'Av. General Genes 234, Lambaré',
                'contacto_nombre': 'Andrea Ruiz',
                'contacto_telefono': '+595985556677',
                'is_active': True
            },

            # ==================== AIRE ACONDICIONADO ====================
            {
                'ruc': '80156789-5',
                'razon_social': 'CLIMA AUTOMOTRIZ S.A.',
                'nombre_fantasia': 'Clima Car',
                'telefono': '+59521378901',
                'email': 'tecnico@climacar.com.py',
                'ciudad': 'Asunción',
                'direccion': 'Calle Palma 567, Asunción',
                'contacto_nombre': 'José López',
                'contacto_telefono': '+595986667788',
                'is_active': True
            },

            # ==================== PROVEEDORES INACTIVOS ====================
            {
                'ruc': '80167890-6',
                'razon_social': 'REPUESTOS USADOS S.R.L.',
                'nombre_fantasia': 'Repuestos Económicos',
                'telefono': '+59521389012',
                'email': 'info@repmotos.com.py',
                'ciudad': 'Asunción',
                'direccion': 'Av. Perú 345, Asunción',
                'contacto_nombre': 'Roberto Castro',
                'contacto_telefono': '+595987778899',
                'is_active': False
            },
            {
                'ruc': '80178901-7',
                'razon_social': 'ACCESORIOS DECORATIVOS S.A.',
                'nombre_fantasia': 'Accesorios Style',
                'telefono': '+59521390123',
                'email': 'ventas@accesoriosstyle.com.py',
                'ciudad': 'San Lorenzo',
                'direccion': 'Ruta 1 Km 10, San Lorenzo',
                'contacto_nombre': 'María Torres',
                'contacto_telefono': '+595988889900',
                'is_active': False
            },

            # ==================== PROVEEDORES ESPECIALIZADOS ====================
            {
                'ruc': '80189012-8',
                'razon_social': 'SISTEMAS DE ESCAPE S.R.L.',
                'nombre_fantasia': 'Escape Total',
                'telefono': '+59521401234',
                'email': 'tecnica@escapetotal.com.py',
                'ciudad': 'Fernando de la Mora',
                'direccion': 'Av. Defensores del Chaco 678, Fernando de la Mora',
                'contacto_nombre': 'Carlos Rivas',
                'contacto_telefono': '+595989990011',
                'is_active': True
            },
            {
                'ruc': '80190123-9',
                'razon_social': 'SUSPENSIÓN Y DIRECCIÓN S.A.',
                'nombre_fantasia': 'Suspensión Pro',
                'telefono': '+59521412345',
                'email': 'ventas@suspensionpro.com.py',
                'ciudad': 'Luque',
                'direccion': 'Calle Comercio 901, Luque',
                'contacto_nombre': 'Diego Martínez',
                'contacto_telefono': '+595981001122',
                'is_active': True
            }
        ]

        created_count = 0
        updated_count = 0
        errores = []

        for proveedor_data in proveedores:
            # Buscar por RUC (único)
            ruc = proveedor_data['ruc']
            try:
                proveedor = Proveedor.objects.get(ruc=ruc)
                # Actualizar proveedor existente
                for key, value in proveedor_data.items():
                    setattr(proveedor, key, value)
                
                proveedor.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'⮐ {proveedor_data["razon_social"]} - {ruc} (actualizado)'))
            except Proveedor.DoesNotExist:
                try:
                    # Crear nuevo proveedor
                    Proveedor.objects.create(**proveedor_data)
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ {proveedor_data["razon_social"]} - {ruc}'))
                except Exception as e:
                    errores.append(f"Error con {proveedor_data['razon_social']} - {ruc}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f'✗ {proveedor_data["razon_social"]} - {ruc}: {str(e)}'))
            except Exception as e:
                errores.append(f"Error con {proveedor_data['razon_social']} - {ruc}: {str(e)}")
                self.stdout.write(self.style.ERROR(f'✗ {proveedor_data["razon_social"]} - {ruc}: {str(e)}'))

        # Estadísticas
        total_proveedores = Proveedor.objects.count()
        activos = Proveedor.objects.filter(is_active=True).count()
        inactivos = Proveedor.objects.filter(is_active=False).count()

        # Agrupar por tipo de proveedor (basado en el nombre)
        categorias = {
            'Repuestos': 0,
            'Lubricantes': 0,
            'Herramientas': 0,
            'Neumáticos': 0,
            'Eléctricos': 0,
            'Carrocería': 0,
            'Especializados': 0
        }

        for proveedor in Proveedor.objects.all():
            razon = proveedor.razon_social.upper()
            if any(palabra in razon for palabra in ['REPUESTO', 'AUTOPARTE', 'FILTRO', 'FRENO']):
                categorias['Repuestos'] += 1
            elif any(palabra in razon for palabra in ['LUBRICANTE', 'FLUIDO', 'ACEITE']):
                categorias['Lubricantes'] += 1
            elif any(palabra in razon for palabra in ['HERRAMIENTA', 'EQUIPO', 'DIAGNÓSTICO']):
                categorias['Herramientas'] += 1
            elif any(palabra in razon for palabra in ['NEUMÁTICO', 'LLANTA']):
                categorias['Neumáticos'] += 1
            elif any(palabra in razon for palabra in ['BATERÍA', 'ELÉCTRIC', 'ESCAPE', 'SUSPENSIÓN']):
                categorias['Eléctricos'] += 1
            elif any(palabra in razon for palabra in ['PINTURA', 'CARROCERÍA']):
                categorias['Carrocería'] += 1
            else:
                categorias['Especializados'] += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nProceso completado: {created_count} proveedores creados, {updated_count} proveedores actualizados'
        ))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\nErrores encontrados ({len(errores)}):'))
            for error in errores:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Todos los proveedores se procesaron sin errores'))

        self.stdout.write(self.style.SUCCESS(
            f'Total en sistema: {total_proveedores} proveedores ({activos} activos, {inactivos} inactivos)'
        ))
        
        self.stdout.write(self.style.SUCCESS('\nDistribución por categoría:'))
        for categoria, cantidad in categorias.items():
            if cantidad > 0:
                self.stdout.write(self.style.SUCCESS(f'  - {categoria}: {cantidad}'))
        
        self.stdout.write(self.style.SUCCESS('Proveedores cargados exitosamente!'))