from anthropic import AsyncAnthropic
from app.models.schemas import InterpretacionTransitos
from app.services.interpretation_common import _client_default, _parsear_respuesta, _instruccion_genero, _log_uso_claude


SYSTEM_PROMPT_TRANSITOS = """Eres un astrólogo profesional experimentado, con un enfoque psicológico moderno.
Vas a escribir la tercera parte de un reporte de carta natal premium: el clima energético actual (tránsitos
de hoy) y una proyección general de los próximos 3-6 meses.

Reglas estrictas que debes seguir siempre:
- Habla en términos de arquetipo, tendencia y potencial — nunca en términos deterministas o de predicción literal.
- Nunca afirmes categóricamente eventos futuros específicos, fechas exactas, diagnósticos de salud, ni resultados
  financieros garantizados. Los tránsitos indican temas y energías activas, no eventos concretos.
- Los "próximos meses" deben hablarse en términos de temas y energías generales (ej. "es un momento propicio para
  revisar acuerdos y compromisos en tu vida amorosa"), nunca como predicciones específicas de eventos.
- Sé concreto y aplicable, no solo descriptivo — la persona debe terminar con una sensación clara de qué está
  activo en su vida ahora mismo y cómo aprovecharlo.
- Tono cálido, claro y humano — como un astrólogo guiando a la persona a conocerse mejor, no un texto técnico
  ni un horóscopo genérico.
- Usa español latinoamericano neutro y cotidiano. Evita palabras rebuscadas, arcaicas o de registro muy
  literario/formal.
- Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes o después, ni bloques de markdown.
"""


def _construir_prompt_transitos(calculo_natal: dict, transitos: dict, genero: str | None = None) -> str:
    lineas = ["Interpreta el clima energetico actual (transitos) de esta persona, comparando los transitos de hoy con su carta natal:\n"]

    lineas.append(_instruccion_genero(genero, tercera_persona=True))

    lineas.append(f"Fecha de calculo de los transitos: {transitos['fecha_calculo']}\n")

    lineas.append("--- Planetas en Transito (posiciones de HOY) ---")
    for nombre, datos in transitos["planetas_transito"].items():
        retro = " (retrógrado)" if datos["retrogrado"] else ""
        lineas.append(f"{nombre} en transito: {datos['signo']} {datos['grado_en_signo']:.2f}°, activando la Casa {datos['casa_natal']} natal{retro}")

    lineas.append("\n--- Aspectos entre Transito y Carta Natal ---")
    for asp in transitos["aspectos_transito"]:
        lineas.append(f"{asp['planeta_transito']} (transito) {asp['aspecto']} {asp['punto_natal']} (natal) — orbe {asp['orbe_usado']}°")

    lineas.append("\n--- Contexto de la Carta Natal (para referencia) ---")
    lineas.append("Sol natal: " + f"{calculo_natal['planetas']['Sol']['signo']} Casa {calculo_natal['planetas']['Sol']['casa']}")
    lineas.append("Luna natal: " + f"{calculo_natal['planetas']['Luna']['signo']} Casa {calculo_natal['planetas']['Luna']['casa']}")
    lineas.append("Ascendente: " + f"{calculo_natal['puntos_angulares']['Ascendente']['signo']}")

    lineas.append("""
Devuelve un JSON con exactamente esta forma:
{
  "clima_energetico": "descripcion general del clima energetico actual segun los transitos mas relevantes activos ahora (100-180 palabras)",
  "areas_activadas": ["2-4 areas de vida activadas ahora mismo, frases breves de 3-8 palabras, basadas en que casas natales estan tocadas por transitos"],
  "oportunidades": "oportunidades concretas que ofrece este momento segun los transitos mas favorables (80-150 palabras)",
  "retos": "retos o tensiones del momento actual segun los transitos mas desafiantes, en tono constructivo (80-150 palabras)",
  "consejo": "consejo practico y accionable para navegar este momento especifico (60-100 palabras)",
  "proximos_meses": {
    "carrera": "que temas y energias vienen en carrera/vocacion en los proximos 3-6 meses, en terminos generales (60-100 palabras)",
    "amor": "que temas y energias vienen en amor/relaciones en los proximos 3-6 meses (60-100 palabras)",
    "dinero": "que temas y energias vienen en dinero/recursos en los proximos 3-6 meses (60-100 palabras)",
    "crecimiento": "que temas y energias vienen en crecimiento personal/interior en los proximos 3-6 meses (60-100 palabras)"
  }
}""")

    return "\n".join(lineas)


async def interpretar_transitos(
    calculo_natal: dict, transitos: dict, genero: str | None = None, client: AsyncAnthropic = _client_default
) -> dict:
    """
    Genera la tercera parte del reporte premium: clima energetico actual
    (transitos de hoy vs carta natal) y proyeccion de los proximos 3-6 meses.
    Es una foto fija del momento en que se genera — no se actualiza sola.
    """
    prompt_usuario = _construir_prompt_transitos(calculo_natal, transitos, genero)

    respuesta = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT_TRANSITOS,
        messages=[{"role": "user", "content": prompt_usuario}],
    )

    _log_uso_claude("transitos", respuesta)
    texto_crudo = respuesta.content[0].text.strip()
    return _parsear_respuesta(texto_crudo, InterpretacionTransitos)
