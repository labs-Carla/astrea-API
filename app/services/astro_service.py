import swisseph as swe
import os
from app.core.config import PLANETAS, SIGNOS

_RUTA_EPHE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ephe"))
swe.set_ephe_path(_RUTA_EPHE)
print(f"[DEBUG] Ruta ephemeris configurada: {_RUTA_EPHE}")

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
    swe.set_ephe_path(_RUTA_EPHE)
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

def calcular_posiciones_transito(dia_juliano: float) -> dict:
    """
    Calcula las posiciones planetarias actuales ("de transito") para un dia
    juliano dado, sin necesidad de casas propias (los transitos se leen
    contra las casas de la carta NATAL, no tienen casas propias). Reutiliza
    la misma logica de obtener_signo/velocidad que calcular_posiciones_planetarias,
    pero sin el calculo de casa (eso se hace aparte, comparando contra la
    carta natal via determinar_casa_natal).
    """
    swe.set_ephe_path(_RUTA_EPHE)
    posiciones = {}

    for nombre, codigo in PLANETAS.items():
        resultado, _ = swe.calc_ut(dia_juliano, codigo, FLAGS)
        longitud_eclip = resultado[0]
        velocidad = resultado[3]

        signo, grado_en_signo = obtener_signo(longitud_eclip)

        posiciones[nombre] = {
            "longitud_absoluta": longitud_eclip,
            "signo": signo,
            "grado_en_signo": grado_en_signo,
            "velocidad": velocidad,
            "retrogrado": velocidad < 0,
        }

    return posiciones


def determinar_casa_natal(grado_absoluto: float, casas_natales: dict) -> int:
    """
    Determina en que casa NATAL cae un grado absoluto (tipicamente la
    posicion de un planeta en transito), comparando contra las cuspides
    ya calculadas de la carta natal. casas_natales es el dict {numero: {...}}
    que ya devuelve calcular_casas().

    Recorre las 12 casas en orden y verifica si el grado cae en el arco
    entre la cuspide de esa casa y la cuspide de la siguiente (manejando
    el caso de que el arco cruce el 0°/360°).
    """
    grado_absoluto = grado_absoluto % 360

    for numero_casa in range(1, 13):
        cuspide_actual = casas_natales[numero_casa]["longitud_absoluta"]
        siguiente_numero = numero_casa + 1 if numero_casa < 12 else 1
        cuspide_siguiente = casas_natales[siguiente_numero]["longitud_absoluta"]

        if cuspide_actual < cuspide_siguiente:
            if cuspide_actual <= grado_absoluto < cuspide_siguiente:
                return numero_casa
        else:
            # El arco cruza 0°/360° (ej. cuspide en 350°, siguiente en 20°)
            if grado_absoluto >= cuspide_actual or grado_absoluto < cuspide_siguiente:
                return numero_casa

    return 1  # fallback, no deberia llegar aqui si las 12 cuspides estan bien formadas