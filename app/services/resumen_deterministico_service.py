"""
Genera el resumen gratuito de forma determinística (sin llamada a Claude),
combinando textos fijos por signo para Sol, Luna y Ascendente, estructurados
como 3 tarjetas: identidad / emociones / camino.

Decisión de producto: las llamadas a Claude se reservan exclusivamente para
después de la compra del reporte premium. El resumen gratuito nunca debe
generar costo de IA ni ser vulnerable a abuso (llamadas repetidas sin control
de un usuario que solo cambia ligeramente sus datos de entrada).
"""

SOL_TEXTOS = {
    "Aries": "Tu Sol en Aries te da una identidad marcada por la iniciativa y el coraje. Necesitas actuar, liderar y avanzar — la impaciencia con lo lento es parte de tu naturaleza.",
    "Tauro": "Tu Sol en Tauro construye tu identidad desde la estabilidad y el placer sensorial. Buscas seguridad y disfrutas de lo tangible: lo que puedes tocar, saborear y conservar.",
    "Geminis": "Tu Sol en Géminis te define por la curiosidad y la necesidad de comunicar. Tu identidad se nutre de ideas nuevas, conversaciones y la posibilidad de cambiar de tema.",
    "Cancer": "Tu Sol en Cáncer construye tu identidad alrededor del cuidado y la memoria emocional. Necesitas un hogar, literal o simbólico, donde sentirte protegido para poder brillar.",
    "Leo": "Tu Sol en Leo te da una identidad expresiva y generosa. Necesitas ser visto y reconocido — brillar no es vanidad, es tu forma natural de dar y recibir amor.",
    "Virgo": "Eres una mente analítica y detallista, con una fuerte necesidad de servicio y mejora constante.",
    "Libra": "Tu Sol en Libra te define por la búsqueda de equilibrio y conexión. Tu identidad se completa en el vínculo con otros, y la armonía es una necesidad, no un lujo.",
    "Escorpio": "Tu Sol en Escorpio construye tu identidad desde la intensidad y la transformación. Necesitas profundidad — lo superficial simplemente no te sostiene.",
    "Sagitario": "Tu Sol en Sagitario te da una identidad expansiva y optimista. Buscas sentido a través de la exploración, ya sea física, filosófica o espiritual.",
    "Capricornio": "Tu Sol en Capricornio construye tu identidad desde la disciplina y el logro. Necesitas estructura y resultados tangibles para sentir que tu vida tiene dirección.",
    "Acuario": "Tu Sol en Acuario te define por la originalidad y la visión colectiva. Tu identidad se afirma al ser diferente y al pensar en sistemas más grandes que tú mismo.",
    "Piscis": "Tu Sol en Piscis construye tu identidad desde la sensibilidad y la conexión con lo intangible. Necesitas espacio para soñar, sentir y disolver los límites rígidos.",
}

LUNA_TEXTOS = {
    "Aries": "Tu mundo emocional es directo e impaciente: sientes rápido y necesitas expresarlo de inmediato, sin filtros.",
    "Tauro": "Tu mundo emocional busca calma y constancia: te calmas con lo físico, lo predecible y lo placentero.",
    "Geminis": "Tu mundo emocional necesita palabras: procesas lo que sientes hablándolo, escribiéndolo o pensándolo en voz alta.",
    "Cancer": "Tu mundo emocional es profundo y protector: necesitas sentirte en casa, con vínculos donde la vulnerabilidad sea segura.",
    "Leo": "Tu mundo emocional necesita reconocimiento: sientes con intensidad y necesitas que ese sentir sea visto y valorado.",
    "Virgo": "Tu mundo emocional se calma sirviendo y ordenando: te sientes mejor cuando puedes hacer algo útil con lo que sientes.",
    "Libra": "Tu mundo emocional busca equilibrio en la relación: te cuesta sentirte bien si hay conflicto o desconexión cerca.",
    "Escorpio": "Tu mundo emocional es intenso y profundo: necesitas verdad y no toleras la superficialidad en los vínculos.",
    "Sagitario": "Tu mundo emocional necesita libertad: te sientes bien cuando puedes moverte, explorar y no sentirte atrapado.",
    "Capricornio": "Tu mundo emocional se contiene y estructura: sientes mucho por dentro, aunque hacia afuera prefieres mostrar control.",
    "Acuario": "Tu mundo emocional es profundo e independiente. Necesitas libertad mental y conexión auténtica para sentirte en paz.",
    "Piscis": "Tu mundo emocional es poroso y compasivo: absorbes lo que sienten los demás casi tan fácil como lo tuyo propio.",
}

ASCENDENTE_TEXTOS = {
    "Aries": "Tu ascendente en Aries te da una presencia directa y valiente. Vienes a iniciar y a atreverte donde otros dudan.",
    "Tauro": "Tu ascendente en Tauro te da una presencia calmada y estable. Vienes a construir algo duradero, a tu propio ritmo.",
    "Geminis": "Tu ascendente en Géminis te da una presencia curiosa y ágil. Vienes a conectar ideas y personas que de otro modo no se cruzarían.",
    "Cancer": "Tu ascendente en Cáncer te da una presencia cálida y protectora. Vienes a cuidar y a crear espacios donde otros se sientan seguros.",
    "Leo": "Tu ascendente en Leo te da una presencia magnética y luminosa. Vienes a expresarte sin pedir permiso.",
    "Virgo": "Tu ascendente en Virgo te da una presencia meticulosa y confiable. Vienes a mejorar lo que tocas.",
    "Libra": "Tu ascendente en Libra te da una presencia agradable y armoniosa. Vienes a equilibrar y a conectar.",
    "Escorpio": "Tu ascendente en Escorpio te da una presencia magnética y una intuición poderosa. Vienes a transformarte y transformar tu entorno.",
    "Sagitario": "Tu ascendente en Sagitario te da una presencia optimista y expansiva. Vienes a explorar y a expandir horizontes, los tuyos y los de otros.",
    "Capricornio": "Tu ascendente en Capricornio te da una presencia seria y capaz. Vienes a construir estructuras que perduren.",
    "Acuario": "Tu ascendente en Acuario te da una presencia original e independiente. Vienes a romper moldes que ya no sirven.",
    "Piscis": "Tu ascendente en Piscis te da una presencia sensible y difícil de definir del todo. Vienes a disolver límites rígidos y a conectar con lo intangible.",
}

ELEMENTO_TEXTOS = {
    "Fuego": "Tu elemento dominante es Fuego: actúas por impulso e inspiración, y necesitas espacio para expresarte con espontaneidad.",
    "Tierra": "Tu elemento dominante es Tierra: construyes desde lo tangible y lo constante, y necesitas resultados concretos para sentirte segura.",
    "Aire": "Tu elemento dominante es Aire: piensas y conectas ideas con facilidad, y necesitas estímulo mental para sentirte viva.",
    "Agua": "Tu elemento dominante es Agua: sientes con profundidad e intuyes antes de razonar, y necesitas espacio emocional genuino.",
}

MODALIDAD_TEXTOS = {
    "Cardinal": "Tu modalidad dominante es Cardinal: inicias más de lo que sostienes, y te energiza empezar cosas nuevas.",
    "Fijo": "Tu modalidad dominante es Fijo: sostienes lo que empiezas con determinación, y te cuesta soltar lo que ya construiste.",
    "Mutable": "Tu modalidad dominante es Mutable: te adaptas con facilidad al cambio, y te resulta natural ajustar el rumbo sobre la marcha.",
}

ASPECTO_PLANTILLAS = {
    "Conjuncion": "Tu {a} y tu {b} están en conjunción — actúan casi como una sola fuerza en tu carta, reforzándose mutuamente sin fricción.",
    "Trigono": "Tu {a} y tu {b} forman un trígono — fluyen con facilidad entre sí, una combinación que te resulta natural y armoniosa.",
    "Sextil": "Tu {a} y tu {b} forman un sextil — hay una oportunidad de colaboración entre ambos que se activa cuando decides usarla.",
    "Cuadratura": "Tu {a} y tu {b} forman una cuadratura — una tensión productiva que te empuja a crecer, aunque a veces se sienta como fricción interna.",
    "Oposicion": "Tu {a} y tu {b} están en oposición — viven en una polaridad que pide equilibrio consciente entre ambos extremos.",
}

NOMBRES_LEGIBLES = {"Sol": "Sol", "Luna": "Luna", "Ascendente": "Ascendente"}
PARES_BIG_THREE = [("Sol", "Luna"), ("Sol", "Ascendente"), ("Luna", "Ascendente")]


def _buscar_aspecto_destacado(aspectos: list[dict]) -> dict | None:
    """
    Busca si alguno de los 3 pares del Big Three (Sol-Luna, Sol-Ascendente,
    Luna-Ascendente) forma un aspecto mayor. Retorna el primero que encuentre
    (los aspectos ya vienen ordenados por orbe más cerrado desde aspectos_service),
    o None si ninguno de los tres pares tiene aspecto dentro del orbe permitido.
    """
    for par_a, par_b in PARES_BIG_THREE:
        for asp in aspectos:
            puntos = {asp["punto_a"], asp["punto_b"]}
            if puntos == {par_a, par_b}:
                return {"par": (par_a, par_b), "aspecto": asp["aspecto"]}
    return None


def generar_resumen_deterministico(calculo: dict) -> dict:
    """
    Combina los textos fijos de Sol, Luna y Ascendente en 3 tarjetas
    independientes (identidad / emociones / camino), más el elemento y
    modalidad dominantes, y el aspecto destacado entre el Big Three (si existe).
    Todo determinístico, sin ninguna llamada a IA.

    Retorna un dict con esta forma:
    {
      "identidad": {"titulo": "Tu identidad", "texto": "...", "etiqueta": "Sol en Virgo en Casa 10"},
      "emociones": {"titulo": "Tus emociones", "texto": "...", "etiqueta": "Luna en Acuario en Casa 4"},
      "camino":    {"titulo": "Tu camino", "texto": "...", "etiqueta": "Ascendente en Escorpio"},
      "elemento_modalidad": {"titulo": "Tu balance elemental", "texto": "..."},
      "aspecto_destacado": {"titulo": "Un patrón en tu Big Three", "texto": "..."} | None
    }
    """
    sol = calculo["planetas"]["Sol"]
    luna = calculo["planetas"]["Luna"]
    asc = calculo["puntos_angulares"]["Ascendente"]

    resultado = {
        "identidad": {
            "titulo": "Tu identidad",
            "texto": SOL_TEXTOS.get(sol["signo"], ""),
            "etiqueta": f"Sol en {sol['signo']} en Casa {sol['casa']}",
        },
        "emociones": {
            "titulo": "Tus emociones",
            "texto": LUNA_TEXTOS.get(luna["signo"], ""),
            "etiqueta": f"Luna en {luna['signo']} en Casa {luna['casa']}",
        },
        "camino": {
            "titulo": "Tu camino",
            "texto": ASCENDENTE_TEXTOS.get(asc["signo"], ""),
            "etiqueta": f"Ascendente en {asc['signo']}",
        },
    }

    elementos_y_modalidades = calculo.get("elementos_y_modalidades")
    if elementos_y_modalidades:
        elemento_dom = elementos_y_modalidades.get("elemento_dominante")
        modalidad_dom = elementos_y_modalidades.get("modalidad_dominante")
        texto_elemento = ELEMENTO_TEXTOS.get(elemento_dom, "")
        texto_modalidad = MODALIDAD_TEXTOS.get(modalidad_dom, "")
        resultado["elemento_modalidad"] = {
            "titulo": "Tu balance elemental",
            "texto": f"{texto_elemento} {texto_modalidad}".strip(),
            "conteo_elementos": elementos_y_modalidades.get("conteo_elementos", {}),
        }

    aspectos = calculo.get("aspectos", [])
    encontrado = _buscar_aspecto_destacado(aspectos)
    if encontrado:
        par_a, par_b = encontrado["par"]
        plantilla = ASPECTO_PLANTILLAS.get(encontrado["aspecto"])
        if plantilla:
            resultado["aspecto_destacado"] = {
                "titulo": "Un patrón en tu Big Three",
                "texto": plantilla.format(a=NOMBRES_LEGIBLES[par_a], b=NOMBRES_LEGIBLES[par_b]),
            }

    return resultado