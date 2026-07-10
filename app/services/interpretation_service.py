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
- IMPORTANTE: teje conexiones entre los distintos bloques usando los aspectos proporcionados (ej. si el Sol
  está en cuadratura con Saturno, menciónalo al hablar del Sol). También conecta patrones de signo/casa
  repetidos. La carta debe leerse como un relato con hilo conductor, no como fragmentos desconectados.
- Prioriza mencionar con más peso los planetas en casas angulares (1, 4, 7, 10), ya que son más determinantes en
  la vida de la persona.
- Tono cálido, claro y humano — como un astrólogo guiando a la persona a conocerse mejor, no un texto técnico
  ni un horóscopo genérico.
- Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes o después, ni bloques de markdown.
"""


def _construir_prompt_usuario(calculo: dict) -> str:
    planetas = calculo["planetas"]
    puntos_angulares = calculo["puntos_angulares"]
    aspectos = calculo.get("aspectos", [])
    dignidades = calculo.get("dignidades", {})
    elementos = calculo.get("elementos_y_modalidades", {})

    lineas = ["Interpreta esta carta natal completa:\n"]
    lineas.append("--- Puntos Angulares ---")
    for nombre, datos in puntos_angulares.items():
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°")

    lineas.append("\n--- Planetas y Puntos ---")
    for nombre, datos in planetas.items():
        retro = " (retrógrado)" if datos["retrogrado"] else ""
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°, Casa {datos['casa']}{retro}")

    if dignidades:
        lineas.append("\n--- Dignidades Esenciales ---")
        for nombre, info in dignidades.items():
            lineas.append(f"{nombre} en {info['signo']}: {info['dignidad']}")

    if elementos:
        lineas.append("\n--- Balance de Elementos y Modalidades ---")
        lineas.append(f"Elementos: {elementos['conteo_elementos']}")
        lineas.append(f"Elemento dominante: {elementos['elemento_dominante']}")
        lineas.append(f"Modalidades: {elementos['conteo_modalidades']}")
        lineas.append(f"Modalidad dominante: {elementos['modalidad_dominante']}")

    if aspectos:
        lineas.append("\n--- Aspectos ---")
        for asp in aspectos:
            lineas.append(f"{asp['punto_a']} {asp['aspecto']} {asp['punto_b']} (orbe {asp['orbe_usado']}°)")

    lineas.append("""
Devuelve un JSON con exactamente esta forma (todas las claves en minúsculas, sin tildes en las claves):
{
  "overview": "resumen general que amarra toda la carta (150-250 palabras)",
  "lectura_elementos_dignidades": "interpretación dedicada al patrón de Elementos/Modalidades y Dignidades Esenciales (100-180 palabras). Esta NO es una repetición del overview, es su propia lectura enfocada:
    (1) Explica qué arquetipo resulta de la COMBINACIÓN del elemento dominante y la modalidad dominante juntos
        (ej. Aire+Mutable no es 'mente ágil' + 'adaptable' por separado, sino un único rasgo compuesto:
        curiosidad conectiva que salta de idea en idea sin anclar). No listes los conteos numéricos, intégralos en la narrativa.
    (2) Si hay planetas con dignidad esencial (Domicilio o Exaltación), interpreta qué dice de la carta tener
        esa fuerza concentrada ahí — son las herramientas más confiables de la persona.
    (3) Si hay planetas en Caída o Exilio, interpreta qué tensión o área de esfuerzo consciente representan —
        sin tono negativo, como potencial que requiere trabajo. Omite cualquier planeta sin dignidad marcada.
    (4) Cierra conectando el patrón elemento/modalidad con el patrón de dignidades: ¿el estilo dominante
        ayuda o compite con las áreas de fuerza/tensión que marcan las dignidades?",
  "sol": "...", "luna": "...", "mercurio": "...", "venus": "...", "marte": "...",
  "jupiter": "...", "saturno": "...", "urano": "...", "neptuno": "...", "pluton": "...",
  "nodo_norte": "...", "quiron": "...", "ascendente": "...", "medio_cielo": "...",
  "conclusion": "cierre del reporte (100-150 palabras) dirigido directamente al lector, como una carta cálida —
    no un resumen de los capítulos anteriores. Debe transmitir que esta carta natal no es un veredicto, sino una
    invitación a conocerse con mayor profundidad, vivir con más conciencia y elegir el propio camino. Debe sugerir
    que la comprensión de esta carta evoluciona con la experiencia de vida, y que volver a leerla en distintos
    momentos puede revelar significados nuevos. La frase final debe dejar una sensación de apertura e inspiración,
    como el cierre de un buen libro, invitando al lector a continuar escribiendo su propia historia. Tono cálido y
    esperanzador, sin frases grandilocuentes ni excesivamente espirituales.",
  "frase_de_cierre": "una frase breve y memorable (máximo 200 caracteres) para la última página del reporte, que
    sintetice el espíritu único de ESTA carta específica (no una frase genérica de horóscopo). Debe sentirse como
    algo que el lector querría subrayar, fotografiar o recordar. Sin clichés espirituales ni frases grandilocuentes."
}
Cada bloque de planeta/punto individual: 100-180 palabras. Si un planeta tiene dignidad esencial
(Domicilio, Exaltación, Caída o Exilio), menciónalo explícitamente en su interpretación individual,
explicando qué significa esa fortaleza o debilidad para ese planeta específico.""")

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