from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from servicio.models import Servicio, ServicioInsumo
from insumo.models import Insumo


class Command(BaseCommand):
    help = 'Carga servicios iniciales para el taller Iam Car'

    @transaction.atomic
    def handle(self, *args, **options):
        servicios = [
            # ===================== MANTENIMIENTO BÁSICO =====================
            {
                "nombre": "Cambio de aceite y filtro",
                "descripcion": "Cambio completo de aceite motor y filtro de aceite. Incluye verificación de niveles.",
                "categoria": "MANTENIMIENTO",
                "mano_obra": Decimal("150000.00"),
                "comision_porcentaje": Decimal("15.00"),  # 15%
                "tiempo_min_estimado": 60,
                "insumos": [
                    {"nombre": "Aceite Motor 10W40 Sintético", "cantidad": Decimal("4.50")},
                    {"nombre": "Filtro de aceite spin-on (M20x1.5)", "cantidad": Decimal("1.00")},
                ]
            },
            {
                "nombre": "Cambio de aceite semi-sintético",
                "descripcion": "Cambio de aceite semi-sintético y filtro para vehículos de uso regular.",
                "categoria": "MANTENIMIENTO",
                "mano_obra": Decimal("120000.00"),
                "comision_porcentaje": Decimal("15.00"),  # 15%
                "tiempo_min_estimado": 45,
                "insumos": [
                    {"nombre": "Aceite Motor 5W30 Semi-Sintético", "cantidad": Decimal("4.50")},
                    {"nombre": "Filtro de aceite spin-on (3/4\"-16)", "cantidad": Decimal("1.00")},
                ]
            },
            {
                "nombre": "Cambio de filtro de aire",
                "descripcion": "Reemplazo de filtro de aire del motor.",
                "categoria": "MANTENIMIENTO",
                "mano_obra": Decimal("50000.00"),
                "comision_porcentaje": Decimal("20.00"),  # 20% - servicio rápido
                "tiempo_min_estimado": 35,
                "insumos": [
                    {"nombre": "Filtro de aire panel (mediano)", "cantidad": Decimal("1.00")},
                ]
            },
            {
                "nombre": "Cambio de filtro de aire de cabina",
                "descripcion": "Reemplazo de filtro de polen/cabina.",
                "categoria": "MANTENIMIENTO",
                "mano_obra": Decimal("45000.00"),
                "comision_porcentaje": Decimal("20.00"),  # 20% - servicio rápido
                "tiempo_min_estimado": 30,
                "insumos": [
                    {"nombre": "Filtro de aire de cabina (polen)", "cantidad": Decimal("1.00")},
                ]
            },
            {
                "nombre": "Cambio de filtro de combustible",
                "descripcion": "Reemplazo de filtro de combustible y purga del sistema para mantener el rendimiento del motor.",
                "categoria": "MANTENIMIENTO",
                "mano_obra": Decimal("60000.00"),
                "comision_porcentaje": Decimal("18.00"),  # 18%
                "tiempo_min_estimado": 30,
                "insumos": [
                    {"nombre": "Filtro de combustible metálico o cartucho", "cantidad": Decimal("1.00")},
                ]
            },
            {
                "nombre": "Service completo 10.000 km",
                "descripcion": "Service completo incluye cambio de aceite, filtros y verificación de 25 puntos.",
                "categoria": "MANTENIMIENTO",
                "mano_obra": Decimal("250000.00"),
                "comision_porcentaje": Decimal("12.00"),  # 12% - servicio complejo
                "tiempo_min_estimado": 120,
                "insumos": [
                    {"nombre": "Aceite Motor 10W40 Sintético", "cantidad": Decimal("4.50")},
                    {"nombre": "Filtro de aceite spin-on (M20x1.5)", "cantidad": Decimal("1.00")},
                    {"nombre": "Filtro de aire panel (mediano)", "cantidad": Decimal("1.00")},
                    {"nombre": "Filtro de aire de cabina (polen)", "cantidad": Decimal("1.00")},
                ]
            },

            # ===================== SISTEMA DE FRENOS =====================
            {
                "nombre": "Cambio de pastillas de freno delanteras",
                "descripcion": "Reemplazo de pastillas de freno delanteras con verificación de discos.",
                "categoria": "FRENOS",
                "mano_obra": Decimal("180000.00"),
                "comision_porcentaje": Decimal("18.00"),  # 18% - servicio de seguridad
                "tiempo_min_estimado": 60,
                "insumos": [
                    {"nombre": "Pastillas de freno NAO (orgánicas) - juego delantero", "cantidad": Decimal("1.00")},
                    {"nombre": "Líquido de frenos DOT 4", "cantidad": Decimal("0.20")},
                ]
            },
            {
                "nombre": "Cambio de pastillas de freno premium",
                "descripcion": "Reemplazo con pastillas cerámicas premium para mayor durabilidad.",
                "categoria": "FRENOS",
                "mano_obra": Decimal("220000.00"),
                "comision_porcentaje": Decimal("20.00"),  # 20% - servicio premium
                "tiempo_min_estimado": 70,
                "insumos": [
                    {"nombre": "Pastillas de freno Cerámicas Premium - juego delantero", "cantidad": Decimal("1.00")},
                    {"nombre": "Líquido de frenos DOT 4", "cantidad": Decimal("0.25")},
                ]
            },
            {
                "nombre": "Cambio de discos y pastillas de freno delanteras",
                "descripcion": "Reemplazo completo de discos y pastillas de freno delanteras con ajuste del sistema.",
                "categoria": "FRENOS",
                "mano_obra": Decimal("280000.00"),
                "comision_porcentaje": Decimal("22.00"),  # 22% - trabajo complejo
                "tiempo_min_estimado": 90,
                "insumos": [
                    {"nombre": "Discos de freno ventilados (par)", "cantidad": Decimal("1.00")},
                    {"nombre": "Pastillas de freno semi-metálicas (juego delantero)", "cantidad": Decimal("1.00")},
                ]
            },

            # ===================== SUSPENSIÓN Y DIRECCIÓN =====================
            {
                "nombre": "Alineación y balanceo",
                "descripcion": "Alineación de dirección y balanceo de las 4 ruedas.",
                "categoria": "SUSPENSION",
                "mano_obra": Decimal("120000.00"),
                "comision_porcentaje": Decimal("25.00"),  # 25% - servicio especializado
                "tiempo_min_estimado": 60,
                "insumos": [
                    {"nombre": "Plomos de balanceo adhesivos 5/10 g (caja)", "cantidad": Decimal("0.10")},
                ]
            },
            {
                "nombre": "Cambio de amortiguadores delanteros",
                "descripcion": "Reemplazo de amortiguadores delanteros completos.",
                "categoria": "SUSPENSION",
                "mano_obra": Decimal("300000.00"),
                "comision_porcentaje": Decimal("20.00"),  # 20% - trabajo pesado
                "tiempo_min_estimado": 120,
                "insumos": [
                    {"nombre": "Amortiguador delantero a gas (par)", "cantidad": Decimal("1.00")},
                    {"nombre": "Kit guardapolvo + tope (delantero)", "cantidad": Decimal("1.00")},
                ]
            },

            # ===================== TRANSMISIÓN =====================
            {
                "nombre": "Cambio de aceite de caja manual",
                "descripcion": "Reemplazo de aceite para caja de cambios manual.",
                "categoria": "TRANSMISION",
                "mano_obra": Decimal("100000.00"),
                "comision_porcentaje": Decimal("18.00"),  # 18%
                "tiempo_min_estimado": 50,
                "insumos": [
                    {"nombre": "Aceite Engranajes 75W-90 (GL-5)", "cantidad": Decimal("2.50")},
                ]
            },
            {
                "nombre": "Cambio de filtro de transmisión automática",
                "descripcion": "Reemplazo del filtro de transmisión automática y del fluido ATF.",
                "categoria": "TRANSMISION",
                "mano_obra": Decimal("250000.00"),
                "comision_porcentaje": Decimal("25.00"),  # 25% - trabajo especializado
                "tiempo_min_estimado": 150,
                "insumos": [
                    {"nombre": "Filtro de transmisión automática", "cantidad": Decimal("1.00")},
                    {"nombre": "ATF Dexron III", "cantidad": Decimal("4.00")},
                ]
            },

            # ===================== MOTOR Y PERFORMANCE =====================
            {
                "nombre": "Lavado de inyectores",
                "descripcion": "Limpieza profesional del sistema de inyección.",
                "categoria": "MOTOR",
                "mano_obra": Decimal("150000.00"),
                "comision_porcentaje": Decimal("20.00"),  # 20% - servicio técnico
                "tiempo_min_estimado": 60,
                "insumos": [
                    {"nombre": "Aceite Motor 10W40 Sintético", "cantidad": Decimal("0.50")},
                ]
            },
            {
                "nombre": "Cambio de bujías",
                "descripcion": "Reemplazo de juego completo de bujías.",
                "categoria": "MOTOR",
                "mano_obra": Decimal("80000.00"),
                "comision_porcentaje": Decimal("25.00"),  # 25% - servicio rápido y técnico
                "tiempo_min_estimado": 40,
                "insumos": [
                    {"nombre": "Grasa Multipropósito NLGI 2", "cantidad": Decimal("0.05")},
                ]
            },

            # ===================== ELECTRICIDAD Y ELECTRÓNICA =====================
            {
                "nombre": "Diagnóstico eléctrico computarizado",
                "descripcion": "Escaneo completo de sistemas electrónicos del vehículo.",
                "categoria": "ELECTRICIDAD",
                "mano_obra": Decimal("80000.00"),
                "comision_porcentaje": Decimal("30.00"),  # 30% - diagnóstico especializado
                "tiempo_min_estimado": 30,
                "insumos": []
            },
            {
                "nombre": "Instalación de sistema de alarma",
                "descripcion": "Instalación profesional de sistema de alarma vehicular.",
                "categoria": "ELECTRICIDAD",
                "mano_obra": Decimal("200000.00"),
                "comision_porcentaje": Decimal("25.00"),  # 25% - instalación técnica
                "tiempo_min_estimado": 120,
                "insumos": []
            },

            # ===================== CHAPERÍA Y PINTURA =====================
            {
                "nombre": "Reparación de abolladuras leves",
                "descripcion": "Desabollado de piezas sin necesidad de repintado, utilizando técnicas PDR (Paintless Dent Repair).",
                "categoria": "CHAPERIA_PINTURA",
                "mano_obra": Decimal("180000.00"),
                "comision_porcentaje": Decimal("30.00"),  # 30% - especialidad
                "tiempo_min_estimado": 90,
                "insumos": [
                    {"nombre": "Herramientas PDR", "cantidad": Decimal("0.05")},
                ]
            },
            {
                "nombre": "Pintura completa de vehículo",
                "descripcion": "Pintado integral del vehículo con preparación de superficie, primer, base color y laca.",
                "categoria": "CHAPERIA_PINTURA",
                "mano_obra": Decimal("2500000.00"),
                "comision_porcentaje": Decimal("15.00"),  # 15% - trabajo extenso
                "tiempo_min_estimado": 1440,
                "insumos": [
                    {"nombre": "Masilla poliéster automotriz", "cantidad": Decimal("2.00")},
                    {"nombre": "Primer acrílico gris", "cantidad": Decimal("1.50")},
                    {"nombre": "Pintura base color", "cantidad": Decimal("3.00")},
                    {"nombre": "Laca transparente 2K", "cantidad": Decimal("2.00")},
                ]
            },
            {
                "nombre": "Pulido y abrillantado",
                "descripcion": "Pulido completo con compuestos abrasivos y encerado final para restaurar el brillo de la pintura.",
                "categoria": "CHAPERIA_PINTURA",
                "mano_obra": Decimal("350000.00"),
                "comision_porcentaje": Decimal("35.00"),  # 35% - trabajo artesanal
                "tiempo_min_estimado": 180,
                "insumos": [
                    {"nombre": "Pasta de pulir gruesa", "cantidad": Decimal("0.20")},
                    {"nombre": "Pasta de pulir fina", "cantidad": Decimal("0.20")},
                    {"nombre": "Cera de terminación", "cantidad": Decimal("0.10")},
                ]
            },
        ]

        created_count = 0
        updated_count = 0

        for servicio_data in servicios:
            # Extraer datos de insumos
            insumos_data = servicio_data.pop('insumos', [])
            
            # Buscar por nombre (único)
            nombre = servicio_data['nombre']
            try:
                # Usar get_or_create para manejar la creación/actualización
                servicio, created = Servicio.objects.get_or_create(
                    nombre=nombre,
                    defaults=servicio_data
                )
                
                if not created:
                    # Actualizar servicio existente
                    for key, value in servicio_data.items():
                        setattr(servicio, key, value)
                    servicio.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'⮐ {nombre} (actualizado)'))
                else:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ {nombre}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error con {nombre}: {str(e)}'))
                continue

            # Limpiar insumos existentes antes de asignar nuevos
            ServicioInsumo.objects.filter(servicio=servicio).delete()

            # Procesar insumos del servicio
            insumos_procesados = 0
            for insumo_data in insumos_data:
                try:
                    insumo_nombre = insumo_data['nombre']
                    cantidad = insumo_data['cantidad']
                    
                    # Buscar el insumo por nombre
                    insumo = Insumo.objects.get(nombre=insumo_nombre)
                    
                    # Crear relación ServicioInsumo
                    ServicioInsumo.objects.create(
                        servicio=servicio,
                        insumo=insumo,
                        cantidad=cantidad
                    )
                    
                    insumos_procesados += 1
                    
                except Insumo.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'   ✗ Insumo no encontrado: {insumo_nombre}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ✗ Error con insumo {insumo_nombre}: {e}'))

            if insumos_procesados > 0:
                self.stdout.write(self.style.SUCCESS(f'   → {insumos_procesados} insumo(s) asignado(s)'))

            # Actualizar costo de insumos del servicio
            try:
                servicio.actualizar_costo_insumos()
                self.stdout.write(self.style.SUCCESS(f'   → Costo de insumos actualizado: Gs. {servicio.costo_insumos:,.0f}'))
                self.stdout.write(self.style.SUCCESS(f'   → Comisión: {servicio.comision_porcentaje}% (≈ Gs. {servicio.mano_obra * servicio.comision_porcentaje / 100:,.0f})'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ Error actualizando costo: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nProceso completado: {created_count} servicios creados, {updated_count} servicios actualizados'
        ))
        self.stdout.write(self.style.SUCCESS('Servicios cargados exitosamente!'))