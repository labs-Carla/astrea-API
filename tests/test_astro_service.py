import swisseph as swe
import pytest

from app.domain.astro_constants import PLANETAS
from app.services.astro_service import (
    obtener_signo,
    calcular_casa_natural,
    calcular_casas,
    calcular_casa_de_planeta,
    calcular_posiciones_planetarias,
    calcular_posiciones_transito,
)

# J2000.0, epoca de referencia estandar en astronomia (2000-01-01 12:00 UT).
DIA_JULIANO_J2000 = swe.julday(2000, 1, 1, 12.0)
LATITUD_BSAS = -34.6
LONGITUD_BSAS = -58.4


def test_obtener_signo_inicio_de_signo():
    assert obtener_signo(0.0) == ("Aries", 0.0)


def test_obtener_signo_mitad_de_signo():
    signo, grado = obtener_signo(35.0)
    assert signo == "Tauro"
    assert grado == 5.0


def test_obtener_signo_normaliza_grados_mayores_a_360():
    signo, grado = obtener_signo(365.0)
    assert signo == "Aries"
    assert grado == 5.0


def test_calcular_casa_natural_mismo_signo_es_casa_1():
    assert calcular_casa_natural("Aries", "Aries") == 1


def test_calcular_casa_natural_ejemplo_del_docstring():
    # Venus en Cancer para una persona Aries activa su Casa 4 natural.
    assert calcular_casa_natural("Cancer", "Aries") == 4


def test_calcular_casa_natural_envuelve_el_zodiaco():
    # Piscis es el ultimo signo antes de volver a Aries -> Casa 12.
    assert calcular_casa_natural("Piscis", "Aries") == 12


def test_calcular_casas_devuelve_12_casas_con_signo_y_grado():
    resultado = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)

    assert set(resultado["casas"].keys()) == set(range(1, 13))
    for casa in resultado["casas"].values():
        assert 0 <= casa["longitud_absoluta"] < 360
        assert 0 <= casa["grado_en_signo"] < 30
        assert casa["signo"]

    assert "Ascendente" in resultado["puntos_angulares"]
    assert "MedioCielo" in resultado["puntos_angulares"]
    assert "_armc" in resultado


def test_calcular_casas_casa_1_coincide_con_ascendente():
    # Invariante astrologica: la cuspide de la Casa 1 ES el Ascendente.
    resultado = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)
    assert resultado["casas"][1]["longitud_absoluta"] == pytest.approx(
        resultado["puntos_angulares"]["Ascendente"]["longitud_absoluta"]
    )


def test_calcular_casas_casa_10_coincide_con_mediocielo():
    # Invariante astrologica (sistema Placidus): la cuspide de la Casa 10 ES el Medio Cielo.
    resultado = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)
    assert resultado["casas"][10]["longitud_absoluta"] == pytest.approx(
        resultado["puntos_angulares"]["MedioCielo"]["longitud_absoluta"]
    )


def test_calcular_casas_valores_conocidos_j2000_buenos_aires():
    # Test de regresion: valores reales de Swiss Ephemeris para una fecha/lugar fijos.
    resultado = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)

    ascendente = resultado["puntos_angulares"]["Ascendente"]
    assert ascendente["signo"] == "Acuario"
    assert ascendente["longitud_absoluta"] == pytest.approx(320.1316, abs=1e-3)

    mediocielo = resultado["puntos_angulares"]["MedioCielo"]
    assert mediocielo["signo"] == "Escorpio"
    assert mediocielo["longitud_absoluta"] == pytest.approx(224.5187, abs=1e-3)


def test_calcular_posiciones_planetarias_incluye_todos_los_planetas():
    casas = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)
    posiciones = calcular_posiciones_planetarias(DIA_JULIANO_J2000, LATITUD_BSAS, casas["_armc"])

    assert set(posiciones.keys()) == set(PLANETAS.keys())
    for planeta in posiciones.values():
        assert 0 <= planeta["longitud_absoluta"] < 360
        assert planeta["signo"]
        assert isinstance(planeta["retrogrado"], bool)
        assert 1 <= planeta["casa"] <= 12


def test_calcular_posiciones_planetarias_valores_conocidos_j2000():
    # Test de regresion contra valores reales de Swiss Ephemeris.
    casas = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)
    posiciones = calcular_posiciones_planetarias(DIA_JULIANO_J2000, LATITUD_BSAS, casas["_armc"])

    sol = posiciones["Sol"]
    assert sol["signo"] == "Capricornio"
    assert sol["longitud_absoluta"] == pytest.approx(280.3689, abs=1e-3)
    assert sol["casa"] == 11
    assert sol["retrogrado"] is False

    # Saturno esta retrogrado en esta fecha (velocidad negativa) — cubre esa rama.
    assert posiciones["Saturno"]["retrogrado"] is True
    assert posiciones["Saturno"]["velocidad"] < 0


def test_calcular_posiciones_transito_no_calcula_casa():
    # A diferencia de calcular_posiciones_planetarias, el transito no tiene
    # datos de nacimiento (latitud/armc) para ubicar una casa propia.
    transito = calcular_posiciones_transito(DIA_JULIANO_J2000)

    assert set(transito.keys()) == set(PLANETAS.keys())
    for planeta in transito.values():
        assert "casa" not in planeta


def test_calcular_posiciones_transito_coincide_con_planetarias_salvo_la_casa():
    # Ambas funciones calculan la misma posicion planetaria cruda; solo
    # calcular_posiciones_planetarias le suma el dato de casa natal.
    casas = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)
    posiciones = calcular_posiciones_planetarias(DIA_JULIANO_J2000, LATITUD_BSAS, casas["_armc"])
    transito = calcular_posiciones_transito(DIA_JULIANO_J2000)

    for nombre in PLANETAS:
        for campo in ("longitud_absoluta", "signo", "grado_en_signo", "velocidad", "retrogrado"):
            assert transito[nombre][campo] == posiciones[nombre][campo]


def test_calcular_casa_de_planeta_coincide_con_la_casa_de_posiciones_planetarias():
    # calcular_posiciones_planetarias usa calcular_casa_de_planeta internamente
    # para cada planeta — verificamos que el wrapper devuelva lo mismo standalone.
    casas = calcular_casas(DIA_JULIANO_J2000, LATITUD_BSAS, LONGITUD_BSAS)
    posiciones = calcular_posiciones_planetarias(DIA_JULIANO_J2000, LATITUD_BSAS, casas["_armc"])

    sol = posiciones["Sol"]
    casa_sol = calcular_casa_de_planeta(
        DIA_JULIANO_J2000, LATITUD_BSAS, casas["_armc"], sol["longitud_absoluta"]
    )

    assert int(casa_sol) == sol["casa"]
    assert 1 <= casa_sol < 13
