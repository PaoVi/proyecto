"""
Utilidades para generación de documentos de factura.
"""

from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from seguridad.models import ConfiguracionSistema


def get_config(clave, default=""):
    """Obtener configuración del sistema"""
    try:
        return ConfiguracionSistema.objects.get(clave=clave, activo=True).valor
    except ConfiguracionSistema.DoesNotExist:
        return default


def generar_pdf_factura(factura):
    """
    Genera el PDF de una factura utilizando la plantilla HTML
    factura/pdf_factura.html.

    Args:
        factura: instancia del modelo Factura.

    Returns:
        bytes: archivo PDF generado.
    """
    
    # Obtener configuración del taller
    config = {
        "nombre_taller": get_config("nombre_taller", "TALLER AUTOMOTRIZ"),
        "ruc_taller": get_config("ruc_taller", "—"),
        "direccion_taller": get_config("direccion_taller", "—"),
        "telefono_taller": get_config("telefono_taller", "—"),
    }
    
    # Determinar marca (si está anulada)
    marca = "ANULADA" if factura.estado == "ANULADA" else ""
    
    html = render_to_string(
        "factura/pdf_factura.html",
        {
            "factura": factura,
            "config": config,
            "marca": marca,
        }
    )

    # Generar PDF con weasyprint
    pdf = HTML(string=html).write_pdf()
    
    return pdf