from anthropic import AsyncAnthropic
from app.models.schemas import InterpretacionResumen
from app.services.interpretation_common import _client_default, _parsear_respuesta, _log_uso_claude


SYSTEM_PROMPT_RESUMEN = """Eres un astrólogo profesional experimentado, con un enfoque psicológico moderno.
Vas a escribir el resumen gratuito de una carta natal, que funciona como preview de un reporte premium
de más de 40 páginas.

Reglas estrictas:
- Enfócate en el Big Three (Sol, Luna, Ascendente) y máximo 1-2 patrones adicionales que más destaquen
  (ej. un stellium, un aspecto muy marcado entre puntos angulares).
- Habla en términos de arquetipo y tendencia — nunca determinista ni de predicción literal.
- Tono cálido y humano, que genere curiosidad genuina de seguir leyendo.
- IMPORTANTE: este es un teaser, no el reporte completo. No profundices en cada planeta ni en cada casa.
  Deja temas como amor, vocación, dinero y heridas emocionales fuera — esos son el gancho del premium,
  no deben resolverse aquí.
- Extensión: 400-600 palabras, en un solo bloque de texto corrido (no subtítulos ni listas).
- Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes o después, ni bloques de markdown.
"""


def _construir_prompt_resumen(calculo: dict) -> str:
    planetas = calculo["planetas"]
    puntos_angulares = calculo["puntos_angulares"]
    aspectos = calculo.get("aspectos", [])

    lineas = ["Escribe el resumen gratuito (teaser) de esta carta natal:\n"]
    lineas.append("--- Puntos Angulares ---")
    for nombre, datos in puntos_angulares.items():
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°")

    lineas.append("\n--- Planetas y Puntos ---")
    for nombre, datos in planetas.items():
        retro = " (retrógrado)" if datos["retrogrado"] else ""
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°, Casa {datos['casa']}{retro}")

    if aspectos:
        lineas.append("\n--- Aspectos ---")
        for asp in aspectos:
            lineas.append(f"{asp['punto_a']} {asp['aspecto']} {asp['punto_b']} (orbe {asp['orbe_usado']}°)")

    lineas.append("""
Devuelve un JSON con exactamente esta forma:
{
  "resumen": "texto de 400-600 palabras centrado en Sol, Luna, Ascendente y 1-2 patrones destacados"
}""")

    return "\n".join(lineas)


async def interpretar_resumen_gratuito(calculo: dict, client: AsyncAnthropic = _client_default) -> dict:
    """
    Genera el resumen gratuito (teaser) de la carta natal, con su propia
    llamada a Claude, independiente y más liviana que interpretar_carta_completa.
    Retorna un dict validado, o un fallback con _validation_error si falla.
    """
    prompt_usuario = _construir_prompt_resumen(calculo)

    respuesta = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT_RESUMEN,
        messages=[{"role": "user", "content": prompt_usuario}],
    )

    _log_uso_claude("resumen_gratuito", respuesta)
    texto_crudo = respuesta.content[0].text.strip()
    return _parsear_respuesta(texto_crudo, InterpretacionResumen)
