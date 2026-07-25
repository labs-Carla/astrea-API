import json
from anthropic import AsyncAnthropic
from pydantic import ValidationError
from app.core.config import settings
from app.models.schemas import InterpretacionCompleta, InterpretacionResumen, InterpretacionAreasDeVida, InterpretacionTransitos



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
- Usa español latinoamericano neutro y cotidiano. Evita palabras rebuscadas, arcaicas o de registro muy
  literario/formal (ej. "escrutadora", "acuciante", "otrora") — prefiere el equivalente natural y directo
  que usaría alguien hablando en la vida diaria (ej. "analítica", "urgente", "antes"). El tono cálido y
  humano debe sentirse también en el vocabulario, no solo en la actitud.
- Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes o después, ni bloques de markdown.
"""


def _construir_prompt_usuario(calculo: dict, genero: str | None = None) -> str:
    planetas = calculo["planetas"]
    puntos_angulares = calculo["puntos_angulares"]
    aspectos = calculo.get("aspectos", [])
    dignidades = calculo.get("dignidades", {})
    elementos = calculo.get("elementos_y_modalidades", {})

    lineas = ["Interpreta esta carta natal completa:\n"]

    if genero == "femenino":
        lineas.append("Genero de la persona: femenino. Ajusta la concordancia gramatical de adjetivos y participios a femenino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente — el mismo estilo narrativo natural que usarias si no conocieras el genero, solo que con las terminaciones correctas.\n")
    elif genero == "masculino":
        lineas.append("Genero de la persona: masculino. Ajusta la concordancia gramatical de adjetivos y participios a masculino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente — el mismo estilo narrativo natural que usarias si no conocieras el genero, solo que con las terminaciones correctas.\n")
    else:
        lineas.append("IMPORTANTE: no se especifico el genero de la persona. Usa lenguaje neutro donde sea posible.\n")


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
  "carta_en_una_mirada": {
    "esencia": "EXACTAMENTE 3 conceptos de UNA SOLA PALABRA cada uno (adjetivos o sustantivos breves), separados por
      ' · ', que capturen el eje central de la carta en una frase-titular (ej. 'Analítica · Transformadora ·
      Sensible'). Nunca frases de 2+ palabras por concepto. Deben ser palabras distintas a las que usarás
      luego en el overview — es un titular, no un adelanto textual.",
    "talentos": ["3 a 4 fortalezas MUY breves (2-5 palabras cada una), como titulares de periódico, no oraciones
      completas. Ej: 'Comprender a las personas', 'Resolver problemas complejos'. NO expliques el porqué aquí
      — eso se desarrolla después en los capítulos."],
    "desafios": ["3 a 4 desafíos MUY breves, mismo formato que talentos. Ej: 'Tendencia al perfeccionismo',
      'Exceso de análisis'. Sin explicar el porqué."],
    "mision": "un párrafo breve (80-150 palabras) que sintetice el camino evolutivo de la carta con SU PROPIO
      ángulo narrativo, distinto al de la conclusión final. Trata este párrafo como la contraportada de un
      libro: genera intriga y dirección, no desarrollo completo."
  },
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
    algo que el lector querría subrayar, fotografiar o recordar. Sin clichés espirituales ni frases grandilocuentes.
    SIEMPRE en segunda persona (tú), hablandole directo al lector (ej. 'Tienes todo lo que necesitas...'), NUNCA en
    tercera persona impersonal (evita 'tiene', 'necesita' sin sujeto).",

}

IMPORTANTE sobre "carta_en_una_mirada": esta sección es un resumen ejecutivo de dos minutos, no un adelanto
textual de lo que sigue. Usa lenguaje, ángulos y énfasis DISTINTOS a los que usarás en el overview y en los
capítulos de planetas — evita reutilizar las mismas frases o metáforas que emplearás después en el reporte.

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

async def interpretar_carta_completa(calculo: dict, genero: str | None = None) -> dict:
    """
    Genera la interpretación narrativa completa de la carta natal usando Claude,
    en una sola llamada para permitir que el texto teja conexiones entre puntos.
    genero (opcional) ajusta la concordancia de genero en espanol del texto generado.
    Retorna un dict validado, o un fallback con _validation_error si la respuesta no cumple el esquema.
    """
    prompt_usuario = _construir_prompt_usuario(calculo, genero)

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


async def interpretar_resumen_gratuito(calculo: dict) -> dict:
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

    texto_crudo = respuesta.content[0].text.strip()
    texto_limpio = _limpiar_json_markdown(texto_crudo)

    try:
        datos_json = json.loads(texto_limpio)
        resumen_validado = InterpretacionResumen(**datos_json)
        return resumen_validado.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        return {
            "_validation_error": str(e),
            "_raw_response": texto_crudo,
        }

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

    lineas = ["Escribe la segunda parte del reporte de esta carta natal (areas de vida practicas):\n"]

    if genero == "femenino":
        lineas.append("Genero de la persona: femenino. Ajusta la concordancia gramatical de adjetivos y participios a femenino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente — el mismo estilo narrativo natural que usarias si no conocieras el genero, solo que con las terminaciones correctas.\n")
    elif genero == "masculino":
        lineas.append("Genero de la persona: masculino. Ajusta la concordancia gramatical de adjetivos y participios a masculino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente — el mismo estilo narrativo natural que usarias si no conocieras el genero, solo que con las terminaciones correctas.\n")
    else:
        lineas.append("IMPORTANTE: no se especifico el genero de la persona. Usa lenguaje neutro donde sea posible.\n")

    lineas.append("--- Puntos Angulares ---")

    lineas.append("\n--- Planetas y Puntos ---")
    for nombre, datos in planetas.items():
        retro = " (retrógrado)" if datos["retrogrado"] else ""
        lineas.append(f"{nombre}: {datos['signo']} {datos['grado_en_signo']:.2f}°, Casa {datos['casa']}{retro}")

    if quiron:
        lineas.append(f"\n--- Quiron (para Herida y Don) ---")
        lineas.append(f"Quiron: {quiron['signo']} {quiron['grado_en_signo']:.2f}°, Casa {quiron['casa']}")

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

async def interpretar_areas_de_vida(calculo: dict, genero: str | None = None) -> dict:
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

    texto_crudo = respuesta.content[0].text.strip()
    texto_limpio = _limpiar_json_markdown(texto_crudo)

    try:
        datos_json = json.loads(texto_limpio)
        interpretacion_validada = InterpretacionAreasDeVida(**datos_json)
        return interpretacion_validada.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        return {
            "_validation_error": str(e),
            "_raw_response": texto_crudo,
        }

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

    if genero == "femenino":
        lineas.append("Genero de la persona: femenino. Ajusta la concordancia gramatical de adjetivos y participios a femenino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente.\n")
    elif genero == "masculino":
        lineas.append("Genero de la persona: masculino. Ajusta la concordancia gramatical de adjetivos y participios a masculino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente.\n")
    else:
        lineas.append("IMPORTANTE: no se especifico el genero de la persona. Usa lenguaje neutro donde sea posible.\n")

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


async def interpretar_transitos(calculo_natal: dict, transitos: dict, genero: str | None = None) -> dict:
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

    texto_crudo = respuesta.content[0].text.strip()
    texto_limpio = _limpiar_json_markdown(texto_crudo)

    try:
        datos_json = json.loads(texto_limpio)
        interpretacion_validada = InterpretacionTransitos(**datos_json)
        return interpretacion_validada.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        return {
            "_validation_error": str(e),
            "_raw_response": texto_crudo,
        }

       