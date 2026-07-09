import swisseph as swe
from app.core.config import PLANETAS, SIGNOS

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

def obtener_signo(grado_absoluto: float) -> tuple[str, float]:
    grado_absoluto = grado_absoluto % 360
    indice_signo = int(grado_absoluto // 30)
    grado_en_signo = grado_absoluto % 30
    return SIGNOS[indice_signo], grado_en_signo


def calcular_casas(dia_juliano: float, latitud: float, longitud: float) -> dict:
    cusps, ascmc = swe.houses_ex(dia_juliano, latitud, longitud, b'P')

    armc = ascmc[2]  # ARMC oficial, ya calculado por swisseph

    casas = {}
    for indice, grado_cuspide in enumerate(cusps):
        numero_casa = indice + 1
        signo, grado_en_signo = obtener_signo(grado_cuspide)
        casas[numero_casa] = {
            "longitud_absoluta": grado_cuspide,
            "signo": signo,
            "grado_en_signo": grado_en_signo,
        }

    ascendente_signo, ascendente_grado = obtener_signo(ascmc[0])
    medio_cielo_signo, medio_cielo_grado = obtener_signo(ascmc[1])

    puntos_angulares = {
        "Ascendente": {
            "longitud_absoluta": ascmc[0],
            "signo": ascendente_signo,
            "grado_en_signo": ascendente_grado,
        },
        "MedioCielo": {
            "longitud_absoluta": ascmc[1],
            "signo": medio_cielo_signo,
            "grado_en_signo": medio_cielo_grado,
        },
    }

    return {"casas": casas, "puntos_angulares": puntos_angulares, "_armc": armc}


def calcular_casa_de_planeta(dia_juliano: float, latitud: float, armc: float,
                               longitud_planeta: float, latitud_eclip_planeta: float = 0.0) -> float:
    oblicuidad = swe.calc_ut(dia_juliano, swe.ECL_NUT, swe.FLG_SWIEPH)[0][0]

    posicion_casa = swe.house_pos(
        armc,
        latitud,
        oblicuidad,
        [longitud_planeta, latitud_eclip_planeta],  # ahora la lista va aquí
        b'P'                                          # y el sistema de casas al final
    )
    return posicion_casa


def calcular_posiciones_planetarias(dia_juliano: float, latitud: float, armc: float) -> dict:
    posiciones = {}

    for nombre, codigo in PLANETAS.items():
        resultado, _ = swe.calc_ut(dia_juliano, codigo, FLAGS)
        longitud_eclip = resultado[0]
        latitud_eclip = resultado[1]
        velocidad = resultado[3]

        signo, grado_en_signo = obtener_signo(longitud_eclip)
        casa = calcular_casa_de_planeta(dia_juliano, latitud, armc, longitud_eclip, latitud_eclip)

        posiciones[nombre] = {
            "longitud_absoluta": longitud_eclip,
            "signo": signo,
            "grado_en_signo": grado_en_signo,
            "velocidad": velocidad,
            "retrogrado": velocidad < 0,
            "casa": int(casa),
        }

    return posiciones