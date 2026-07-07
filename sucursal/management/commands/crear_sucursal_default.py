from django.core.management.base import BaseCommand
from sucursal.models import Sucursal


class Command(BaseCommand):
    help = "Crea la sucursal por defecto (Matriz) si no existe"

    def handle(self, *args, **options):
        sucursal, created = Sucursal.objects.get_or_create(
            nombre="Matriz",
            defaults={
                "direccion": "Dirección principal",
                "telefono": "",
                "establecimiento": "001",
                "punto_emision": "001",
                "activo": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Sucursal '{sucursal.nombre}' creada exitosamente."))
        else:
            self.stdout.write(f"La sucursal '{sucursal.nombre}' ya existe.")
