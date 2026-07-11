from weasyprint import HTML


def generar_pdf_desde_html(html: str) -> bytes:
    """
    Convierte HTML a PDF (formato A4) usando WeasyPrint.
    A diferencia de Playwright, WeasyPrint es síncrono: no abre un navegador,
    interpreta el HTML/CSS directamente con su propio motor de renderizado
    (Pango + Cairo), implementando el estándar CSS Paged Media de forma estricta.
    Los márgenes de página y el fondo viven completamente en el CSS del template
    (reglas @page en carta_report.html), no se pasan como parámetro aquí.
    Retorna los bytes del PDF, listos para guardar o enviar como respuesta HTTP.
    """
    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes