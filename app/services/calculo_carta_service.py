from app.models.schemas import DatosNacimiento
from app.services.time_service import calcular_hora_utc, calcular_dia_juliano
from app.services.astro_service import calcular_casas, calcular_posiciones_planetarias
from app.domain.aspectos_service import calcular_todos_los_aspectos
from app.domain.dignidades_service import calcular_dignidades_de_carta, calcular_elementos_y_modalidades


def calcular_todo(datos: DatosNacimiento, latitud: float, longitud: float) -> dict:
    """
    Ejecuta el cálculo astronómico completo (posiciones, casas, aspectos,
    dignidades, elementos) a partir de coordenadas ya geocodificadas.
    Centraliza esta lógica para no repetirla entre /resumen, /pdf y /compra.
    """
    fecha_utc = calcular_hora_utc(datos.fecha_hora_local, latitud, longitud)
    dia_juliano = calcular_dia_juliano(fecha_utc)

    resultado_casas = calcular_casas(dia_juliano, latitud, longitud)
    posiciones = calcular_posiciones_planetarias(
        dia_juliano, latitud, resultado_casas["_armc"]
    )

    puntos_para_aspectos = {
        nombre: p["longitud_absoluta"] for nombre, p in posiciones.items()
    }
    puntos_para_aspectos["Ascendente"] = resultado_casas["puntos_angulares"]["Ascendente"]["longitud_absoluta"]
    puntos_para_aspectos["MedioCielo"] = resultado_casas["puntos_angulares"]["MedioCielo"]["longitud_absoluta"]

    aspectos = calcular_todos_los_aspectos(puntos_para_aspectos)
    dignidades = calcular_dignidades_de_carta(posiciones)
    elementos_y_modalidades = calcular_elementos_y_modalidades(posiciones)

    return {
        "fecha_utc": fecha_utc,
        "calculo": {
            "planetas": posiciones,
            "casas": resultado_casas["casas"],
            "puntos_angulares": resultado_casas["puntos_angulares"],
            "aspectos": aspectos,
            "dignidades": dignidades,
            "elementos_y_modalidades": elementos_y_modalidades,
            "fecha_hora_utc": fecha_utc.isoformat(),
        },
    }
