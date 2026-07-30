from datetime import datetime, timezone
from app.services.time_service import calcular_dia_juliano
from app.services.astro_service import calcular_posiciones_transito, determinar_casa_natal
from app.services.aspectos_service import calcular_aspectos_transito_natal
from app.core.config import SIGNOS
from app.services.astro_service import calcular_casa_natural


def calcular_transitos_actuales(calculo_natal: dict) -> dict:
    """
    Calcula el "cielo de hoy": posiciones planetarias actuales, en que casa
    NATAL cae cada una, y los aspectos entre los planetas en transito y los
    puntos de la carta natal (planetas + Ascendente + Medio Cielo).

    calculo_natal es el dict ya guardado en calculo_json (con 'planetas' y
    'puntos_angulares' de la carta natal). No requiere geolocalizacion propia:
    las posiciones planetarias tropicales son las mismas en cualquier lugar
    del planeta, solo su casa depende de las cuspides natales.
    """
    ahora_utc = datetime.now(timezone.utc)
    dia_juliano_hoy = calcular_dia_juliano(ahora_utc)

    posiciones_transito = calcular_posiciones_transito(dia_juliano_hoy)

    # Reconstruye las 12 casas natales en el shape que espera determinar_casa_natal
    # (calculo_natal["casas"] ya tiene esa forma: {numero: {longitud_absoluta, signo, grado_en_signo}})
    casas_natales = calculo_natal["casas"]

    for nombre, datos in posiciones_transito.items():
        datos["casa_natal"] = determinar_casa_natal(datos["longitud_absoluta"], casas_natales)

    # Arma los puntos natales (planetas + angulos) para comparar aspectos
    puntos_natales = {
        nombre: datos["longitud_absoluta"]
        for nombre, datos in calculo_natal["planetas"].items()
    }
    puntos_natales["Ascendente"] = calculo_natal["puntos_angulares"]["Ascendente"]["longitud_absoluta"]
    puntos_natales["MedioCielo"] = calculo_natal["puntos_angulares"]["MedioCielo"]["longitud_absoluta"]

    puntos_transito = {
        nombre: datos["longitud_absoluta"]
        for nombre, datos in posiciones_transito.items()
    }

    aspectos_transito = calcular_aspectos_transito_natal(puntos_transito, puntos_natales)

    return {
        "fecha_calculo": ahora_utc.isoformat(),
        "planetas_transito": posiciones_transito,
        "aspectos_transito": aspectos_transito,
    }

def calcular_transitos_por_signo(dia_juliano: float) -> dict:
    """
    Calcula, para cada uno de los 12 signos del zodiaco, en que casa
    "natural" (rueda generica, sin datos de nacimiento reales) cae cada
    planeta en transito hoy. Usado para horoscopos genericos diarios/
    semanales, a diferencia de calcular_transitos_actuales() que compara
    contra una carta natal real especifica.
    """
    posiciones_transito = calcular_posiciones_transito(dia_juliano)

    resultado = {}
    for signo_persona in SIGNOS:
        planetas_con_casa = {}
        for nombre_planeta, datos in posiciones_transito.items():
            planetas_con_casa[nombre_planeta] = {
                **datos,
                "casa_natural": calcular_casa_natural(datos["signo"], signo_persona),
            }
        resultado[signo_persona] = planetas_con_casa

    return resultado