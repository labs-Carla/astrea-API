from anthropic import AsyncAnthropic
from app.models.schemas import InterpretacionAreasDeVida
from app.services.interpretation_common import _client_default, _parsear_respuesta, _instruccion_genero, _log_uso_claude
from app.domain.regentes_service import calcular_regentes_de_casas


SYSTEM_PROMPT_AREAS_DE_VIDA = """Eres un astrólogo profesional experimentado, con un enfoque psicológico moderno
y muy práctico. Vas a escribir la segunda parte de un reporte de carta natal premium: las áreas de vida
concretas (vocación, dinero, amor), la herida y el don de Quirón, la interpretación de los aspectos más
relevantes, y un plan de acción práctico.

Reglas estrictas que debes seguir siempre:
- Habla en términos de arquetipo, tendencia y potencial — nunca en términos deterministas o de predicción literal.
- Nunca afirmes categóricamente eventos futuros específicos, diagnósticos de salud, ni resultados financieros garantizados.
- Sé concreto y aplicable, no solo descriptivo. Estas secciones son las más prácticas del reporte — la persona
  debe terminar de leerlas con ideas claras de qué hacer con la información, no solo con autoconocimiento abstracto.
- Tono cálido, claro y humano — como un astrólogo guiando a la persona a conocerse mejor, no un texto técnico
  ni un horóscopo genérico.
- Usa español latinoamericano neutro y cotidiano. Evita palabras rebuscadas, arcaicas o de registro muy
  literario/formal — prefiere el equivalente natural y directo que usaría alguien hablando en la vida diaria.
- Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes o después, ni bloques de markdown.
- Si una casa relevante para un area de vida (Dinero: Casa 2/8, Amor: Casa 5/7, Vocacion: Casa 10) no tiene
  planetas propios en la carta, NUNCA digas que "faltan datos" o que "no hay indicadores" — en su lugar,
  usa la informacion del regente de esa casa (que se te proporciona explicitamente) y su ubicacion en la
  carta para interpretar esa area con la misma profundidad que si tuviera planetas propios. Esta es la
  tecnica astrologica estandar para casas vacias.
"""


def _filtrar_aspectos_principales(aspectos: list[dict], top_n: int = 10) -> list[dict]:
    """
    Selecciona los aspectos mas relevantes de la carta, ordenados por orbe
    (menor orbe = aspecto mas exacto = mas influyente). Usado para no pedirle
    a Claude que interprete los ~30 aspectos que puede tener una carta, solo
    los que realmente importan.
    """
    return sorted(aspectos, key=lambda a: a["orbe_usado"])[:top_n]


def _construir_prompt_areas_de_vida(calculo: dict, genero: str | None = None) -> str:
    planetas = calculo["planetas"]
    puntos_angulares = calculo["puntos_angulares"]
    aspectos_principales = _filtrar_aspectos_principales(calculo.get("aspectos", []))
    quiron = planetas.get("Quiron")
    regentes = calcular_regentes_de_casas(calculo)

    lineas = ["Escribe la segunda parte del reporte de esta carta natal (areas de vida practicas):\n"]

    lineas.append(_instruccion_genero(genero))

    lineas.append("--- Puntos Angulares ---")
    for nombre, datos in puntos_angulares.items():
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°")

    lineas.append("\n--- Planetas y Puntos ---")
    for nombre, datos in planetas.items():
        retro = " (retrógrado)" if datos["retrogrado"] else ""
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°, Casa {datos['casa']}{retro}")

    if quiron:
        lineas.append(f"\n--- Quiron (para Herida y Don) ---")
        lineas.append(f"Quiron: {quiron['signo']} {quiron['grado_en_signo']:.2f}°, Casa {quiron['casa']}")

    lineas.append("\n--- Regentes de Casas Clave (para interpretar aunque la casa este vacia de planetas) ---")
    casas_relevantes = {2: "Dinero", 5: "Amor/creatividad", 7: "Amor/relaciones", 8: "Dinero compartido/transformacion", 10: "Vocacion/carrera"}
    for numero_casa, area in casas_relevantes.items():
        info = regentes[numero_casa]
        ub = info["ubicacion_regente"]
        retro_txt = " (retrógrado)" if ub["retrogrado"] else ""
        lineas.append(
            f"Casa {numero_casa} ({area}): cúspide en {info['signo_cuspide']}, regida por {info['regente']}, "
            f"que está ubicado en {ub['signo']} {ub['grado_en_signo']:.2f}°, Casa {ub['casa']}{retro_txt}"
        )

    lineas.append("\n--- Aspectos principales a interpretar individualmente ---")
    for asp in aspectos_principales:
        lineas.append(f"{asp['punto_a']} {asp['aspecto']} {asp['punto_b']} (orbe {asp['orbe_usado']}°)")

    lineas.append(f"""
Devuelve un JSON con exactamente esta forma:
{{
  "vocacion": "forma de trabajar, liderazgo, profesiones afines, donde puede destacar y que puede frenarle
    profesionalmente, basado en Medio Cielo, Casa 10, Sol, Saturno y planetas relevantes (150-250 palabras)",
  "dinero": "relacion con el dinero, como genera recursos, bloqueos, oportunidades y estrategias de crecimiento,
    basado en Casa 2, Casa 8, Venus, Jupiter y planetas relevantes (150-250 palabras)",
  "amor": "como ama, que necesita, patrones relacionales, compatibilidad emocional y aprendizajes afectivos,
    basado en Venus, Marte, Luna, Casa 5, Casa 7 y planetas relevantes (150-250 palabras)",
  "herida_y_don": "interpretacion de Quiron enfocada en: que herida representa, como aparece concretamente en
    la vida de la persona, como puede empezar a sanarla, y cual es el don o regalo que existe detras de esa
    herida una vez trabajada (150-250 palabras)",
  "aspectos_interpretados": [
    {{"punto_a": "...", "aspecto": "...", "punto_b": "...", "interpretacion": "que significa este aspecto
      especifico en la vida de la persona, en terminos concretos y aplicables (80-150 palabras)"}}
    // uno de estos objetos por cada aspecto listado arriba, en el mismo orden, EXACTAMENTE con los mismos
    // valores de punto_a/aspecto/punto_b que se te dieron (no los traduzcas ni cambies el formato)
  ],
  "plan_de_accion": {{
    "potencia": ["3-4 fortalezas de esta carta especifica (no genericas) que conviene potenciar activamente, cada una como una frase accionable de 8-15 palabras en SEGUNDA PERSONA (tu/tus), conectada a un dato concreto de la carta (ej. 'Usa tu Marte en domicilio para liderar proyectos donde puedas decidir rapido')"],
    "observa": ["3-4 patrones especificos de esta carta que conviene observar con mas consciencia, mismo formato: 8-15 palabras, segunda persona, conectado a un dato concreto de la carta"],
    "evita": ["3-4 comportamientos o tendencias especificos de esta carta que conviene evitar, mismo formato: 8-15 palabras, segunda persona, conectado a un dato concreto de la carta"],
    "empieza": ["3-4 acciones concretas y accionables (algo que la persona pueda literalmente hacer esta semana) que se desprenden de esta lectura, mismo formato: 8-15 palabras, segunda persona"]
  }},
  "brujula": {{
    "aprendizajes": ["exactamente 5 aprendizajes clave que esta carta ofrece, cada uno una frase breve y memorable"],
    "mantra": "una frase corta tipo mantra personal (menos de 15 palabras), memorable y accionable, que la persona pueda repetirse",
    "frase_final": "frase de cierre potente que sintetiza el espiritu de la carta (40-250 caracteres), distinta en angulo y palabras a cualquier frase que ya se haya usado en otras partes del reporte. SIEMPRE en segunda persona (tú), hablandole directo al lector, NUNCA en tercera persona ni impersonal"
  }}
}}""")

    return "\n".join(lineas)


async def interpretar_areas_de_vida(
    calculo: dict, genero: str | None = None, client: AsyncAnthropic = _client_default
) -> dict:
    """
    Genera la segunda parte del reporte premium: vocacion, dinero, amor,
    herida y don (Quiron), interpretacion de los aspectos mas relevantes,
    plan de accion y brujula personal. Llamada independiente a Claude,
    separada de interpretar_carta_completa para no sobrecargar una sola
    respuesta con demasiadas secciones. genero (opcional) ajusta la
    concordancia de genero en espanol del texto generado.
    """
    prompt_usuario = _construir_prompt_areas_de_vida(calculo, genero)

    respuesta = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        system=SYSTEM_PROMPT_AREAS_DE_VIDA,
        messages=[{"role": "user", "content": prompt_usuario}],
    )

    _log_uso_claude("areas_de_vida", respuesta)
    texto_crudo = respuesta.content[0].text.strip()
    return _parsear_respuesta(texto_crudo, InterpretacionAreasDeVida)
