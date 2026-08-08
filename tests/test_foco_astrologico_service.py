from app.domain.dignidades_service import calcular_dignidades_de_carta, calcular_elementos_y_modalidades
from app.domain.foco_astrologico_service import extraer_foco

SIGNOS_EN_ORDEN = [
    "Aries", "Tauro", "Geminis", "Cancer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]


def _calculo_de_ejemplo() -> dict:
    """
    Carta donde la cúspide de la Casa N cae en el N-ésimo signo (mismo
    patrón que el fixture de test_regentes_service), para que los regentes
    esperados sean predecibles. Las posiciones planetarias se eligen a mano
    para cubrir a propósito: planetas con y sin dignidad esencial, una casa
    vacía (Casa 8, ningún planeta tiene casa=8 -- solo se llega a ella vía
    su regente, Plutón) y puntos que nunca tienen dignidad (Quirón, NodoNorte).
    """
    casas = {i + 1: {"signo": signo} for i, signo in enumerate(SIGNOS_EN_ORDEN)}

    planetas = {
        "Sol":       {"signo": "Leo",         "casa": 5,  "grado_en_signo": 10.0, "retrogrado": False},  # Domicilio
        "Luna":      {"signo": "Piscis",      "casa": 4,  "grado_en_signo": 5.0,  "retrogrado": False},  # sin dignidad
        "Mercurio":  {"signo": "Geminis",     "casa": 3,  "grado_en_signo": 2.0,  "retrogrado": False},  # Domicilio
        "Venus":     {"signo": "Piscis",      "casa": 2,  "grado_en_signo": 20.0, "retrogrado": False},  # Exaltacion
        "Marte":     {"signo": "Aries",       "casa": 1,  "grado_en_signo": 15.0, "retrogrado": False},  # Domicilio
        "Jupiter":   {"signo": "Piscis",      "casa": 9,  "grado_en_signo": 8.0,  "retrogrado": False},  # Domicilio
        "Saturno":   {"signo": "Virgo",       "casa": 6,  "grado_en_signo": 3.0,  "retrogrado": False},  # sin dignidad
        "Urano":     {"signo": "Acuario",     "casa": 11, "grado_en_signo": 1.0,  "retrogrado": False},  # Domicilio
        "Neptuno":   {"signo": "Piscis",      "casa": 12, "grado_en_signo": 25.0, "retrogrado": False},  # Domicilio
        "Pluton":    {"signo": "Capricornio", "casa": 10, "grado_en_signo": 18.0, "retrogrado": False},  # sin dignidad
        "Quiron":    {"signo": "Piscis",      "casa": 7,  "grado_en_signo": 9.0,  "retrogrado": False},  # nunca tiene dignidad
        "NodoNorte": {"signo": "Leo",         "casa": 9,  "grado_en_signo": 14.0, "retrogrado": False},  # nunca tiene dignidad
    }

    aspectos = [
        {"punto_a": "Sol", "punto_b": "Luna", "aspecto": "Conjuncion", "angulo_exacto": 0, "distancia_real": 0.0, "orbe_usado": 0.0},
        {"punto_a": "Marte", "punto_b": "Quiron", "aspecto": "Oposicion", "angulo_exacto": 180, "distancia_real": 178.0, "orbe_usado": 2.0},
        {"punto_a": "Venus", "punto_b": "Jupiter", "aspecto": "Trigono", "angulo_exacto": 120, "distancia_real": 121.0, "orbe_usado": 1.0},
        {"punto_a": "Saturno", "punto_b": "Urano", "aspecto": "Cuadratura", "angulo_exacto": 90, "distancia_real": 89.0, "orbe_usado": 1.0},
    ]

    return {
        "planetas": planetas,
        "casas": casas,
        "puntos_angulares": {},
        "aspectos": aspectos,
        "dignidades": calcular_dignidades_de_carta(planetas),
        "elementos_y_modalidades": calcular_elementos_y_modalidades(planetas),
        "fecha_hora_utc": "2000-01-01T00:00:00+00:00",
    }


def test_criterios_vacio_devuelve_el_calculo_completo_sin_modificar():
    calculo = _calculo_de_ejemplo()
    assert extraer_foco(calculo, {}) == calculo


def test_filtro_por_casas_incluye_planetas_y_regente_de_casa_vacia():
    calculo = _calculo_de_ejemplo()

    resultado = extraer_foco(calculo, {"casas": [1, 8]})

    # Casa 1 (Aries): Marte esta ubicado ahi y ademas es su propio regente.
    # Casa 8 (Escorpio): esta vacia, solo se llega a ella via su regente, Pluton.
    assert set(resultado["planetas_en_foco"].keys()) == {"Marte", "Pluton"}
    assert resultado["casas"][1]["regente"] == "Marte"
    assert resultado["casas"][8]["regente"] == "Pluton"
    assert resultado["casas"][8]["signo_cuspide"] == "Escorpio"


def test_filtro_por_puntos_sin_casas():
    calculo = _calculo_de_ejemplo()

    resultado = extraer_foco(calculo, {"puntos": ["Quiron"]})

    assert set(resultado["planetas_en_foco"].keys()) == {"Quiron"}
    assert resultado["casas"] == {}


def test_combinacion_de_casas_y_puntos_es_union():
    calculo = _calculo_de_ejemplo()

    resultado = extraer_foco(calculo, {"casas": [1], "puntos": ["Quiron"]})

    assert set(resultado["planetas_en_foco"].keys()) == {"Marte", "Quiron"}
    assert 1 in resultado["casas"]


def test_tipos_aspecto_filtra_los_aspectos_del_foco():
    calculo = _calculo_de_ejemplo()

    resultado = extraer_foco(
        calculo,
        {"puntos": ["Sol", "Luna", "Marte", "Quiron"], "tipos_aspecto": ["Conjuncion"]},
    )

    # Del foco (Sol/Luna/Marte/Quiron) hay dos aspectos posibles (Sol-Luna
    # Conjuncion, Marte-Quiron Oposicion) -- tipos_aspecto deja solo el primero.
    assert len(resultado["aspectos"]) == 1
    assert resultado["aspectos"][0]["aspecto"] == "Conjuncion"
    assert {resultado["aspectos"][0]["punto_a"], resultado["aspectos"][0]["punto_b"]} == {"Sol", "Luna"}


def test_solo_con_dignidad_reduce_el_set_de_puntos():
    calculo = _calculo_de_ejemplo()

    # Casa 1 (Marte, con Domicilio) + Casa 4 (regente Luna, sin dignidad).
    resultado = extraer_foco(calculo, {"casas": [1, 4], "solo_con_dignidad": True})

    assert set(resultado["planetas_en_foco"].keys()) == {"Marte"}
    assert set(resultado["dignidades_en_foco"].keys()) == {"Marte"}


def test_incluir_elementos_y_modalidades_solo_cuando_se_pide():
    calculo = _calculo_de_ejemplo()

    con_elementos = extraer_foco(calculo, {"puntos": ["Sol"], "incluir_elementos_y_modalidades": True})
    sin_elementos = extraer_foco(calculo, {"puntos": ["Sol"]})

    assert con_elementos["elementos_y_modalidades"] == calculo["elementos_y_modalidades"]
    assert "elementos_y_modalidades" not in sin_elementos
