from app.domain.regentes_service import calcular_regentes_de_casas


def extraer_foco(calculo: dict, criterios: dict) -> dict:
    """
    Recorta el cálculo completo de una carta (el dict "calculo" que devuelve
    calculo_carta_service.calcular_todo) a solo lo relevante para un producto
    configurable — sin esto, cada producto nuevo necesitaría repetir a mano
    la lógica de "qué planetas/aspectos importan para este reporte" en cada
    prompt, en vez de declararlo una vez como config de datos.

    `criterios` puede combinar cualquiera de estas claves, todas opcionales:
      - "casas": list[int]        -> incluye los planetas ubicados en esas
        casas + el regente de cada una (vía calcular_regentes_de_casas, que
        ya sabe interpretar una casa vacía a través de su regente).
      - "puntos": list[str]        -> puntos específicos por nombre (ej.
        "Quiron", "NodoNorte"), sin importar en qué casa estén. Se combina
        con "casas" por UNIÓN, no por exclusión mutua: ambos criterios
        amplían el mismo conjunto de puntos en foco.
      - "tipos_aspecto": list[str] -> filtra los aspectos ya restringidos al
        foco a solo esos tipos (ej. "Conjuncion", "Oposicion").
      - "solo_con_dignidad": bool  -> reduce el conjunto de puntos en foco a
        la INTERSECCIÓN con los que tienen dignidad esencial
        (calculo["dignidades"]) — se aplica después de unir "casas" y
        "puntos", nunca antes.
      - "incluir_elementos_y_modalidades": bool -> agrega el resumen global
        de elementos/modalidades dominantes. No es filtrable por punto: es
        un dato agregado de toda la carta, no del foco.

    Si `criterios` viene vacío ({}), devuelve `calculo` tal cual, sin
    filtrar — equivalente al reporte de carta natal completa que ya existe
    hoy, para que un producto sin configuración de foco siga funcionando
    igual que el reporte premium actual.

    Devuelve un dict con "casas" (regentes de las casas pedidas),
    "planetas_en_foco", "dignidades_en_foco", "aspectos", y opcionalmente
    "elementos_y_modalidades".
    """
    if not criterios:
        return calculo

    planetas = calculo["planetas"]
    dignidades = calculo["dignidades"]
    aspectos = calculo["aspectos"]

    nombres_en_foco = set()
    casas_en_foco = {}

    casas_pedidas = criterios.get("casas")
    if casas_pedidas:
        regentes = calcular_regentes_de_casas(calculo)
        for numero_casa in casas_pedidas:
            for nombre, datos in planetas.items():
                if datos["casa"] == numero_casa:
                    nombres_en_foco.add(nombre)

            regente_de_casa = regentes[numero_casa]
            nombres_en_foco.add(regente_de_casa["regente"])
            casas_en_foco[numero_casa] = regente_de_casa

    puntos_pedidos = criterios.get("puntos")
    if puntos_pedidos:
        nombres_en_foco.update(puntos_pedidos)

    if criterios.get("solo_con_dignidad"):
        nombres_en_foco &= set(dignidades.keys())

    planetas_en_foco = {
        nombre: planetas[nombre] for nombre in nombres_en_foco if nombre in planetas
    }
    dignidades_en_foco = {
        nombre: dignidades[nombre] for nombre in nombres_en_foco if nombre in dignidades
    }

    aspectos_en_foco = aspectos
    if casas_pedidas or puntos_pedidos:
        # Solo restringimos por pertenencia si efectivamente se pidieron
        # puntos/casas -- si el único criterio activo es "tipos_aspecto",
        # no hay un conjunto de puntos que sirva de referencia para "pertenece
        # al foco", así que no se descarta ningún aspecto por ese lado.
        aspectos_en_foco = [
            aspecto for aspecto in aspectos_en_foco
            if aspecto["punto_a"] in nombres_en_foco or aspecto["punto_b"] in nombres_en_foco
        ]

    tipos_aspecto = criterios.get("tipos_aspecto")
    if tipos_aspecto:
        aspectos_en_foco = [
            aspecto for aspecto in aspectos_en_foco if aspecto["aspecto"] in tipos_aspecto
        ]

    resultado = {
        "casas": casas_en_foco,
        "planetas_en_foco": planetas_en_foco,
        "dignidades_en_foco": dignidades_en_foco,
        "aspectos": aspectos_en_foco,
    }

    if criterios.get("incluir_elementos_y_modalidades"):
        resultado["elementos_y_modalidades"] = calculo["elementos_y_modalidades"]

    return resultado
