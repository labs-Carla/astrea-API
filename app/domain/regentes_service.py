from app.domain.astro_constants import DISPOSITORES_MODERNOS


def calcular_regentes_de_casas(calculo: dict) -> dict:
    """
    Para cada una de las 12 casas, determina su regente (el planeta que rige
    el signo en la cuspide de esa casa, segun regencia moderna) y donde esta
    ubicado ese regente en la carta natal (signo, casa, grado, retrogrado).

    Esto permite interpretar casas VACIAS (sin planetas propios) a traves de
    su regente — tecnica astrologica estandar. Por ejemplo, si la Casa 8 no
    tiene planetas pero su cuspide cae en Escorpio, el regente es Pluton;
    donde este Pluton en la carta (signo/casa) informa el tema de esa casa
    vacia igual de bien que si tuviera planetas propios.
    """
    casas = calculo["casas"]
    planetas = calculo["planetas"]

    regentes = {}
    for numero_str, datos_casa in casas.items():
        numero_casa = int(numero_str)
        signo_cuspide = datos_casa["signo"]
        regente = DISPOSITORES_MODERNOS[signo_cuspide]
        ubicacion_regente = planetas[regente]

        regentes[numero_casa] = {
            "signo_cuspide": signo_cuspide,
            "regente": regente,
            "ubicacion_regente": {
                "signo": ubicacion_regente["signo"],
                "casa": ubicacion_regente["casa"],
                "grado_en_signo": ubicacion_regente["grado_en_signo"],
                "retrogrado": ubicacion_regente["retrogrado"],
            },
        }

    return regentes