from app.core.config import ASPECTOS_MAYORES, ORBE_DEFAULT


def calcular_distancia_angular(grado_a: float, grado_b: float) -> float:
    """
    Calcula la distancia angular más corta entre dos puntos en el círculo
    de 360°. Nunca supera 180°, ya que ese es el máximo posible en un círculo
    (más allá de 180° empiezas a acercarte por el otro lado).
    """
    diferencia = abs(grado_a - grado_b) % 360
    if diferencia > 180:
        diferencia = 360 - diferencia
    return diferencia


def detectar_aspecto(grado_a: float, grado_b: float, orbe: float = ORBE_DEFAULT) -> dict | None:
    """
    Dado el grado absoluto de dos puntos, determina si forman alguno de los
    5 aspectos mayores dentro del orbe permitido. Retorna None si no hay aspecto.
    """
    distancia = calcular_distancia_angular(grado_a, grado_b)

    for nombre_aspecto, angulo_exacto in ASPECTOS_MAYORES.items():
        diferencia_con_exacto = abs(distancia - angulo_exacto)
        if diferencia_con_exacto <= orbe:
            return {
                "aspecto": nombre_aspecto,
                "angulo_exacto": angulo_exacto,
                "distancia_real": round(distancia, 2),
                "orbe_usado": round(diferencia_con_exacto, 2),
            }

    return None


def calcular_todos_los_aspectos(puntos: dict, orbe: float = ORBE_DEFAULT) -> list[dict]:
    """
    Calcula todos los aspectos mayores entre cada par único de puntos.
    `puntos` debe ser un dict {nombre: grado_absoluto} que incluya planetas,
    Ascendente y Medio Cielo.

    Usa combinaciones sin repetición (A-B pero no B-A, y no A-A), para no
    duplicar aspectos ni comparar un punto consigo mismo.

    Excluye explícitamente el par Ascendente-MedioCielo: su relación angular
    es una propiedad estructural del sistema de casas (casi siempre cercana
    a 90°), no un dato astrológico informativo, por lo que reportarla como
    "aspecto" sería redundante o confuso.
    """
    PARES_EXCLUIDOS = {frozenset({"Ascendente", "MedioCielo"})}

    nombres = list(puntos.keys())
    aspectos_encontrados = []

    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            nombre_a = nombres[i]
            nombre_b = nombres[j]

            if frozenset({nombre_a, nombre_b}) in PARES_EXCLUIDOS:
                continue

            resultado = detectar_aspecto(puntos[nombre_a], puntos[nombre_b], orbe)

            if resultado is not None:
                aspectos_encontrados.append({
                    "punto_a": nombre_a,
                    "punto_b": nombre_b,
                    **resultado,
                })

    return aspectos_encontrados