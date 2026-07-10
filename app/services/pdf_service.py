from playwright.async_api import async_playwright


async def generar_pdf_desde_html(html: str) -> bytes:
    """
    Convierte HTML a PDF (formato A4) usando Chromium headless vía Playwright.
    Usa la API asíncrona porque se ejecuta dentro de un endpoint async de FastAPI
    (necesario para poder usar await con la llamada a Claude en el mismo flujo).
    Retorna los bytes del PDF, listos para guardar o enviar como respuesta HTTP.
    """
    async with async_playwright() as p:
        navegador = await p.chromium.launch()
        pagina = await navegador.new_page()
        await pagina.set_content(html, wait_until="networkidle")

        pdf_bytes = await pagina.pdf(
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
        )

        await navegador.close()

    return pdf_bytes