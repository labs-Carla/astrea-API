import os
from weasyprint import HTML

# Carpeta base para resolver rutas relativas dentro del HTML (ej. assets/imagen.png).
# Sin esto, WeasyPrint no tiene forma de saber desde dónde son relativas esas rutas
# cuando el HTML se pasa como string en memoria (no como archivo en disco).
_RUTA_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")


def generar_pdf_desde_html(html: str) -> bytes:
    """
    Convierte HTML a PDF (formato A4) usando WeasyPrint.
    A diferencia de Playwright, WeasyPrint es síncrono: no abre un navegador,
    interpreta el HTML/CSS directamente con su propio motor de renderizado
    (Pango + Cairo), implementando el estándar CSS Paged Media de forma estricta.
    Los márgenes de página y el fondo viven completamente en el CSS del template
    (reglas @page en carta_report.html), no se pasan como parámetro aquí.

    base_url apunta a la carpeta templates/, para que rutas relativas como
    "assets/fondo_portada_nocturno.png" en el HTML se resuelvan correctamente.
    Retorna los bytes del PDF, listos para guardar o enviar como respuesta HTTP.
    """
    pdf_bytes = HTML(string=html, base_url=_RUTA_TEMPLATES).write_pdf()
    return pdf_bytes