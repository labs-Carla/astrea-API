from app.services.resumen_deterministico_service import (
    generar_resumen_deterministico,
    SOL_TEXTOS,
    LUNA_TEXTOS,
    ASCENDENTE_TEXTOS,
)


def _calculo_base() -> dict:
    return {
        "planetas": {
            "Sol": {"signo": "Virgo", "casa": 10},
            "Luna": {"signo": "Acuario", "casa": 4},
        },
        "puntos_angulares": {
            "Ascendente": {"signo": "Escorpio"},
        },
        "elementos_y_modalidades": {
            "elemento_dominante": "Tierra",
            "modalidad_dominante": "Fijo",
            "conteo_elementos": {"Fuego": 1, "Tierra": 4, "Aire": 2, "Agua": 3},
        },
        "aspectos": [],
    }


def test_generar_resumen_deterministico_arma_las_3_tarjetas_del_big_three():
    resultado = generar_resumen_deterministico(_calculo_base())

    assert resultado["identidad"]["texto"] == SOL_TEXTOS["Virgo"]
    assert resultado["identidad"]["etiqueta"] == "Sol en Virgo en Casa 10"

    assert resultado["emociones"]["texto"] == LUNA_TEXTOS["Acuario"]
    assert resultado["emociones"]["etiqueta"] == "Luna en Acuario en Casa 4"

    assert resultado["camino"]["texto"] == ASCENDENTE_TEXTOS["Escorpio"]
    assert resultado["camino"]["etiqueta"] == "Ascendente en Escorpio"


def test_generar_resumen_deterministico_incluye_elemento_y_modalidad_dominante():
    resultado = generar_resumen_deterministico(_calculo_base())

    assert "Tierra" in resultado["elemento_modalidad"]["texto"]
    assert "Fijo" in resultado["elemento_modalidad"]["texto"]


def test_generar_resumen_deterministico_sin_aspecto_destacado_si_big_three_no_aspecta():
    resultado = generar_resumen_deterministico(_calculo_base())
    assert "aspecto_destacado" not in resultado


def test_generar_resumen_deterministico_detecta_aspecto_destacado_del_big_three():
    calculo = _calculo_base()
    calculo["aspectos"] = [
        {"punto_a": "Sol", "punto_b": "Luna", "aspecto": "Trigono", "orbe_usado": 1.0},
    ]

    resultado = generar_resumen_deterministico(calculo)

    assert "aspecto_destacado" in resultado
    assert "Sol" in resultado["aspecto_destacado"]["texto"]
    assert "Luna" in resultado["aspecto_destacado"]["texto"]
