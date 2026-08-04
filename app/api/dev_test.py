from fastapi import APIRouter, Depends

from app.core.admin_auth import verificar_admin_secret
from app.models.schemas import DatosNacimiento
from app.services.time_service import calcular_hora_utc, calcular_dia_juliano
from app.services.astro_service import calcular_casas, calcular_posiciones_planetarias
from app.services.aspectos_service import calcular_todos_los_aspectos
from app.services.dignidades_service import calcular_dignidades_de_carta, calcular_elementos_y_modalidades
from app.services.interpretation_carta_completa import interpretar_carta_completa
from app.services.geocoding_service import geocodificar_ciudad

router = APIRouter()


@router.post("/test-interpretacion-completa", dependencies=[Depends(verificar_admin_secret)])
async def test_interpretacion_completa(datos: DatosNacimiento):
    latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)
    fecha_utc = calcular_hora_utc(datos.fecha_hora_local, latitud, longitud)
    dia_juliano = calcular_dia_juliano(fecha_utc)
    resultado_casas = calcular_casas(dia_juliano, latitud, longitud)
    posiciones = calcular_posiciones_planetarias(dia_juliano, latitud, resultado_casas["_armc"])

    calculo = {
        "planetas": posiciones,
        "puntos_angulares": resultado_casas["puntos_angulares"],
    }

    interpretacion = await interpretar_carta_completa(calculo)
    return {"interpretacion": interpretacion}


@router.post("/test-aspectos", dependencies=[Depends(verificar_admin_secret)])
def test_aspectos(datos: DatosNacimiento):
    latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)
    fecha_utc = calcular_hora_utc(datos.fecha_hora_local, latitud, longitud)
    dia_juliano = calcular_dia_juliano(fecha_utc)
    resultado_casas = calcular_casas(dia_juliano, latitud, longitud)
    posiciones = calcular_posiciones_planetarias(dia_juliano, latitud, resultado_casas["_armc"])

    # Armamos el dict de {nombre: grado_absoluto} con planetas + Ascendente + Medio Cielo
    puntos = {nombre: datos["longitud_absoluta"] for nombre, datos in posiciones.items()}
    puntos["Ascendente"] = resultado_casas["puntos_angulares"]["Ascendente"]["longitud_absoluta"]
    puntos["MedioCielo"] = resultado_casas["puntos_angulares"]["MedioCielo"]["longitud_absoluta"]

    aspectos = calcular_todos_los_aspectos(puntos)

    return {"total_aspectos": len(aspectos), "aspectos": aspectos}


@router.post("/test-dignidades-elementos", dependencies=[Depends(verificar_admin_secret)])
def test_dignidades_elementos(datos: DatosNacimiento):
    latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)
    fecha_utc = calcular_hora_utc(datos.fecha_hora_local, latitud, longitud)
    dia_juliano = calcular_dia_juliano(fecha_utc)
    resultado_casas = calcular_casas(dia_juliano, latitud, longitud)
    posiciones = calcular_posiciones_planetarias(dia_juliano, latitud, resultado_casas["_armc"])

    dignidades = calcular_dignidades_de_carta(posiciones)
    elementos = calcular_elementos_y_modalidades(posiciones)

    return {"dignidades": dignidades, "elementos_y_modalidades": elementos}
