from app.services.regentes_service import calcular_regentes_de_casas

SIGNOS_EN_ORDEN = [
    "Aries", "Tauro", "Geminis", "Cancer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]


def _calculo_rueda_natural() -> dict:
    """
    Carta donde la cuspide de la Casa N cae en el N-esimo signo (Casa 1 =
    Aries, Casa 2 = Tauro, ...), para poder predecir el regente esperado
    de cada casa sin ambiguedad.
    """
    casas = {
        str(i + 1): {"signo": signo}
        for i, signo in enumerate(SIGNOS_EN_ORDEN)
    }

    # Un planeta distinto por cada dispositor moderno usado en DISPOSITORES_MODERNOS,
    # con una ubicacion arbitraria pero completa.
    planetas_regentes = [
        "Marte", "Venus", "Mercurio", "Luna", "Sol",
        "Pluton", "Jupiter", "Saturno", "Urano", "Neptuno",
    ]
    planetas = {
        nombre: {"signo": "Geminis", "casa": 3, "grado_en_signo": 12.5, "retrogrado": False}
        for nombre in planetas_regentes
    }

    return {"casas": casas, "planetas": planetas}


def test_calcular_regentes_de_casas_asigna_el_dispositor_moderno_correcto():
    regentes = calcular_regentes_de_casas(_calculo_rueda_natural())

    assert regentes[1]["signo_cuspide"] == "Aries"
    assert regentes[1]["regente"] == "Marte"

    assert regentes[8]["signo_cuspide"] == "Escorpio"
    assert regentes[8]["regente"] == "Pluton"


def test_calcular_regentes_de_casas_incluye_ubicacion_del_regente():
    regentes = calcular_regentes_de_casas(_calculo_rueda_natural())

    ubicacion = regentes[1]["ubicacion_regente"]
    assert ubicacion == {
        "signo": "Geminis",
        "casa": 3,
        "grado_en_signo": 12.5,
        "retrogrado": False,
    }


def test_calcular_regentes_de_casas_cubre_las_12_casas():
    regentes = calcular_regentes_de_casas(_calculo_rueda_natural())
    assert set(regentes.keys()) == set(range(1, 13))
