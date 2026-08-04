from app.core.config import (
    DOMICILIOS, EXALTACIONES, CAIDAS, EXILIOS,
    ELEMENTOS_POR_SIGNO, MODALIDADES_POR_SIGNO,
)


def calcular_dignidad(planeta: str, signo: str) -> str | None:
    """
    Determina si un planeta tiene dignidad esencial en el signo dado.
    Retorna "Domicilio", "Exaltacion", "Caida", "Exilio", o None si no aplica.
    """
    if planeta in DOMICILIOS and signo in DOMICILIOS[planeta]:
        return "Domicilio"
    if planeta in EXALTACIONES and EXALTACIONES[planeta] == signo:
        return "Exaltacion"
    if planeta in CAIDAS and CAIDAS[planeta] == signo:
        return "Caida"
    if planeta in EXILIOS and signo in EXILIOS[planeta]:
        return "Exilio"
    return None


def calcular_dignidades_de_carta(posiciones: dict) -> dict:
    """
    Calcula la dignidad esencial de cada planeta en la carta.
    Retorna solo los planetas que SÍ tienen alguna dignidad (omite None).
    """
    dignidades_encontradas = {}

    for nombre, datos in posiciones.items():
        signo = datos["signo"]
        dignidad = calcular_dignidad(nombre, signo)
        if dignidad is not None:
            dignidades_encontradas[nombre] = {
                "signo": signo,
                "dignidad": dignidad,
            }

    return dignidades_encontradas


def calcular_elementos_y_modalidades(posiciones: dict) -> dict:
    """
    Cuenta cuántos de los planetas principales caen en cada elemento
    y cada modalidad.
    """
    PLANETAS_PARA_CONTEO = [
        "Sol", "Luna", "Mercurio", "Venus", "Marte",
        "Jupiter", "Saturno", "Urano", "Neptuno", "Pluton",
    ]

    conteo_elementos = {"Fuego": 0, "Tierra": 0, "Aire": 0, "Agua": 0}
    conteo_modalidades = {"Cardinal": 0, "Fijo": 0, "Mutable": 0}

    for nombre in PLANETAS_PARA_CONTEO:
        if nombre not in posiciones:
            continue
        signo = posiciones[nombre]["signo"]
        elemento = ELEMENTOS_POR_SIGNO.get(signo)
        modalidad = MODALIDADES_POR_SIGNO.get(signo)
        if elemento:
            conteo_elementos[elemento] += 1
        if modalidad:
            conteo_modalidades[modalidad] += 1

    elemento_dominante = max(conteo_elementos, key=conteo_elementos.get)
    modalidad_dominante = max(conteo_modalidades, key=conteo_modalidades.get)

    return {
        "conteo_elementos": conteo_elementos,
        "conteo_modalidades": conteo_modalidades,
        "elemento_dominante": elemento_dominante,
        "modalidad_dominante": modalidad_dominante,
    }