from playwright.sync_api import sync_playwright


def generar_pdf_desde_html(html: str) -> bytes:
    """
    Convierte HTML a PDF (formato A4) usando Chromium headless vía Playwright.
    Retorna los bytes del PDF, listos para guardar o enviar como respuesta HTTP.
    """
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page()
        pagina.set_content(html, wait_until="networkidle")

        pdf_bytes = pagina.pdf(
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
        )

        navegador.close()

    return pdf_bytes