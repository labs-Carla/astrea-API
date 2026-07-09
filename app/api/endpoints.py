from fastapi import APIRouter, HTTPException
from app.models.schemas import DatosNacimiento
from app.services.time_service import calcular_hora_utc, calcular_dia_juliano
from app.services.astro_service import calcular_casas, calcular_posiciones_planetarias
from fastapi.responses import HTMLResponse
from app.services.report_service import generar_html_reporte

router = APIRouter()


@router.post("/carta-natal")
def generar_carta_natal(datos: DatosNacimiento):
    try:
        fecha_utc = calcular_hora_utc(datos.fecha_hora_local, datos.latitud, datos.longitud)
        dia_juliano = calcular_dia_juliano(fecha_utc)

        resultado_casas = calcular_casas(dia_juliano, datos.latitud, datos.longitud)
        posiciones = calcular_posiciones_planetarias(
            dia_juliano, datos.latitud, resultado_casas["_armc"]
        )

        return {
            "metadata": {
                "fecha_hora_local": datos.fecha_hora_local.isoformat(),
                "fecha_hora_utc": fecha_utc.isoformat(),
                "dia_juliano": dia_juliano,
                "latitud": datos.latitud,
                "longitud": datos.longitud,
            },
            "calculo": {
                "planetas": posiciones,
                "casas": resultado_casas["casas"],
                "puntos_angulares": resultado_casas["puntos_angulares"],
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/carta-natal/html", response_class=HTMLResponse)
def generar_carta_natal_html(datos: DatosNacimiento):
    try:
        fecha_utc = calcular_hora_utc(datos.fecha_hora_local, datos.latitud, datos.longitud)
        dia_juliano = calcular_dia_juliano(fecha_utc)

        resultado_casas = calcular_casas(dia_juliano, datos.latitud, datos.longitud)
        posiciones = calcular_posiciones_planetarias(
            dia_juliano, datos.latitud, resultado_casas["_armc"]
        )

        metadata = {
            "fecha_hora_local": datos.fecha_hora_local.isoformat(),
            "fecha_hora_utc": fecha_utc.isoformat(),
            "latitud": datos.latitud,
            "longitud": datos.longitud,
        }
        calculo = {
            "planetas": posiciones,
            "casas": resultado_casas["casas"],
            "puntos_angulares": resultado_casas["puntos_angulares"],
        }

        html = generar_html_reporte(metadata, calculo)
        return HTMLResponse(content=html)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))