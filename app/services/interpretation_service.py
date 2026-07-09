import json
from anthropic import AsyncAnthropic
from pydantic import ValidationError
from app.core.config import settings
from app.models.schemas import InterpretacionCompleta

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """Eres un astrólogo profesional experimentado, con un enfoque psicológico moderno.
Interpretas cartas natales completas como quien narra una historia coherente, no como una lista de
fragmentos aislados.

Reglas estrictas que debes seguir siempre:
- Habla en términos de arquetipo, tendencia y potencial — nunca en términos deterministas o de predicción literal.
- Nunca afirmes categóricamente eventos futuros específicos, diagnósticos de salud, ni resultados financieros garantizados.
- Combina siempre las 3 capas de cada punto: qué representa el planeta, cómo se expresa en ese signo, y en qué área de vida se manifiesta según la casa.
- IMPORTANTE: teje conexiones entre los distintos bloques cuando sea relevante (ej. si el Sol y la Luna comparten
  elemento, o si hay un patrón repetido de signos/casas). La carta debe leerse como un relato con hilo conductor,
  no como fragmentos desconectados.
- Prioriza mencionar con más peso los planetas en casas angulares (1, 4, 7, 10), ya que son más determinantes en
  la vida de la persona.
- Tono cálido, claro y humano — como un astrólogo guiando a la persona a conocerse mejor, no un texto técnico
  ni un horóscopo genérico.
- Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes o después, ni bloques de markdown.
"""


def _construir_prompt_usuario(calculo: dict) -> str:
    planetas = calculo["planetas"]
    puntos_angulares = calculo["puntos_angulares"]

    lineas = ["Interpreta esta carta natal completa:\n"]
    lineas.append("--- Puntos Angulares ---")
    for nombre, datos in puntos_angulares.items():
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°")

    lineas.append("\n--- Planetas y Puntos ---")
    for nombre, datos in planetas.items():
        retro = " (retrógrado)" if datos["retrogrado"] else ""
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°, Casa {datos['casa']}{retro}")

    lineas.append("""
Devuelve un JSON con exactamente esta forma (todas las claves en minúsculas, sin tildes en las claves):
{
  "overview": "resumen general que amarra toda la carta (150-250 palabras)",
  "sol": "...", "luna": "...", "mercurio": "...", "venus": "...", "marte": "...",
  "jupiter": "...", "saturno": "...", "urano": "...", "neptuno": "...", "pluton": "...",
  "nodo_norte": "...", "quiron": "...", "ascendente": "...", "medio_cielo": "...",
  "conclusion": "cierre que integra los temas principales (100-150 palabras)"
}
Cada bloque de planeta/punto individual: 100-180 palabras.""")

    return "\n".join(lineas)


def _limpiar_json_markdown(texto: str) -> str:
    """
    Claude a veces envuelve el JSON en bloques markdown (```json ... ```)
    a pesar de que se le pida no hacerlo. Esta función lo quita si aparece.
    """
    texto = texto.strip()
    if texto.startswith("```"):
        # Quita la primera línea (```json o ```) y la última (```)
        lineas = texto.split("\n")
        if lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas and lineas[-1].strip() == "```":
            lineas = lineas[:-1]
        texto = "\n".join(lineas)
    return texto.strip()


async def interpretar_carta_completa(calculo: dict) -> dict:
    """
    Genera la interpretación narrativa completa de la carta natal usando Claude,
    en una sola llamada para permitir que el texto teja conexiones entre puntos.
    Retorna un dict validado, o un fallback con _validation_error si la respuesta no cumple el esquema.
    """
    prompt_usuario = _construir_prompt_usuario(calculo)

    respuesta = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_usuario}],
    )

    texto_crudo = respuesta.content[0].text.strip()
    texto_limpio = _limpiar_json_markdown(texto_crudo)

    try:
        datos_json = json.loads(texto_limpio)
        interpretacion_validada = InterpretacionCompleta(**datos_json)
        return interpretacion_validada.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        return {
            "_validation_error": str(e),
            "_raw_response": texto_crudo,
        }