from django.db import models


class Sucursal(models.Model):
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre")
    direccion = models.TextField(blank=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=50, blank=True, verbose_name="Teléfono")
    establecimiento = models.CharField(max_length=3, default="001", verbose_name="Establecimiento SET")
    punto_emision = models.CharField(max_length=3, default="001", verbose_name="Punto de emisión SET")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
