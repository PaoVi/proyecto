from django.core.management.base import BaseCommand
from factura.models import NotaCredito

class Command(BaseCommand):
    help = 'Actualiza notas de crédito pendientes a aprobadas después de 24 horas'

    def handle(self, *args, **options):
        notas = NotaCredito.objects.filter(estado=NotaCredito.Estado.PENDIENTE)
        actualizadas = 0
        for nota in notas:
            if nota.actualizar_estado_automatico():
                actualizadas += 1
        
        self.stdout.write(self.style.SUCCESS(f'Notas actualizadas: {actualizadas}'))