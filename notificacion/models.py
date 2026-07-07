from django.db import models
from django.utils import timezone

class LogEnvio(models.Model):
    TIPO_CHOICES = (
        ("bienvenida", "Bienvenida"),
        ("orden_lista", "Orden lista"),
        ("bajo_insumo", "Bajo insumo"),
        ("otro", "Otro"),
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="otro")
    referencia_id = models.PositiveIntegerField(null=True, blank=True)  
    email = models.EmailField(blank=True, null=True)
    asunto = models.CharField(max_length=200)
    exito = models.BooleanField(default=False)
    detalle = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(default=timezone.now)
    sucursal = models.ForeignKey(
        'sucursal.Sucursal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Sucursal",
    )

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        estado = "OK" if self.exito else "FALLÓ"
        return f"[{estado}] {self.tipo} -> {self.email} ({self.asunto})"
