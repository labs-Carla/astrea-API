from fastapi import APIRouter, HTTPException
from app.models.schemas import DatosNacimiento
from app.services.time_service import calcular_hora_utc, calcular_dia_juliano
from app.services.astro_service import calcular_casas, calcular_posiciones_planetarias
from fastapi.responses import HTMLResponse
from app.services.report_service import generar_html_reporte
from fastapi.responses import Response
from app.services.pdf_service import generar_pdf_desde_html

from app.services.interpretation_service import interpretar_carta_completa, interpretar_resumen_gratuito

from app.services.aspectos_service import calcular_todos_los_aspectos

from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.services.persistence_service import buscar_carta_existente, guardar_carta, deserializar_carta

from app.services.dignidades_service import calcular_dignidades_de_carta, calcular_elementos_y_modalidades
from app.services.geocoding_service import geocodificar_ciudad


router = APIRouter()


@router.post("/carta-natal")
def generar_carta_natal(datos: DatosNacimiento):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        fecha_utc = calcular_hora_utc(datos.fecha_hora_local, latitud, longitud)
        dia_juliano = calcular_dia_juliano(fecha_utc)

        resultado_casas = calcular_casas(dia_juliano, latitud, longitud)
        posiciones = calcular_posiciones_planetarias(
            dia_juliano, latitud, resultado_casas["_armc"]
        )

        return {
            "metadata": {
                "nombre": datos.nombre,
                "fecha_hora_local": datos.fecha_hora_local.isoformat(),
                "fecha_hora_utc": fecha_utc.isoformat(),
                "dia_juliano": dia_juliano,
                "ciudad": datos.ciudad,
                "pais": datos.pais,
                "latitud": latitud,
                "longitud": longitud,
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
def generar_carta_natal_html(datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        carta_existente = buscar_carta_existente(
            db, datos.fecha_hora_local, latitud, longitud
        )

        if carta_existente is None:
            raise HTTPException(
                status_code=404,
                detail="Esta carta no ha sido generada todavía. Usa /carta-natal/pdf primero.",
            )

        calculo, interpretacion = deserializar_carta(carta_existente)
        metadata = {
            "nombre": datos.nombre,
            "fecha_hora_local": datos.fecha_hora_local.isoformat(),
            "fecha_hora_utc": calculo.get("fecha_hora_utc", ""),
            "ciudad": datos.ciudad,
            "pais": datos.pais,
            "latitud": latitud,
            "longitud": longitud,
        }

        html = generar_html_reporte(metadata, calculo, interpretacion)
        return HTMLResponse(content=html)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
@router.post("/carta-natal/pdf")
async def generar_carta_natal_pdf(datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        # Primero: ¿esta carta ya fue generada antes con estos datos exactos?
        carta_existente = buscar_carta_existente(
            db, datos.fecha_hora_local, latitud, longitud
        )

        if carta_existente is not None:
            calculo, interpretacion = deserializar_carta(carta_existente)
            metadata = {
                "nombre": datos.nombre,
                "fecha_hora_local": datos.fecha_hora_local.isoformat(),
                "fecha_hora_utc": calculo.get("fecha_hora_utc", ""),
                "ciudad": datos.ciudad,
                "pais": datos.pais,
                "latitud": latitud,
                "longitud": longitud,
            }
        else:
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

            metadata = {
                "nombre": datos.nombre,
                "fecha_hora_local": datos.fecha_hora_local.isoformat(),
                "fecha_hora_utc": fecha_utc.isoformat(),
                "ciudad": datos.ciudad,
                "pais": datos.pais,
                "latitud": latitud,
                "longitud": longitud,
            }
            calculo = {
                "planetas": posiciones,
                "casas": resultado_casas["casas"],
                "puntos_angulares": resultado_casas["puntos_angulares"],
                "aspectos": aspectos,
                "dignidades": dignidades,
                "elementos_y_modalidades": elementos_y_modalidades,
                "fecha_hora_utc": fecha_utc.isoformat(),
            }

            interpretacion = await interpretar_carta_completa(calculo)

            guardar_carta(
                db, datos.fecha_hora_local, latitud, longitud, calculo, interpretacion
            )

        html = generar_html_reporte(metadata, calculo, interpretacion)
        pdf_bytes =  generar_pdf_desde_html(html)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=carta_natal.pdf"},
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/carta-natal/resumen")
async def generar_resumen_gratuito(datos: DatosNacimiento):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

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

        calculo = {
            "planetas": posiciones,
            "casas": resultado_casas["casas"],
            "puntos_angulares": resultado_casas["puntos_angulares"],
            "aspectos": aspectos,
        }

        resumen = await interpretar_resumen_gratuito(calculo)

        return {
            "metadata": {
                "nombre": datos.nombre,
                "fecha_hora_local": datos.fecha_hora_local.isoformat(),
                "fecha_hora_utc": fecha_utc.isoformat(),
                "ciudad": datos.ciudad,
                "pais": datos.pais,
                "latitud": latitud,
                "longitud": longitud,
            },
            "calculo": calculo,
            "resumen": resumen.get("resumen", ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test-interpretacion-completa")
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



@router.post("/test-aspectos")
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


@router.post("/test-dignidades-elementos")
def test_dignidades_elementos(datos: DatosNacimiento):
    latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)
    fecha_utc = calcular_hora_utc(datos.fecha_hora_local, latitud, longitud)
    dia_juliano = calcular_dia_juliano(fecha_utc)
    resultado_casas = calcular_casas(dia_juliano, latitud, longitud)
    posiciones = calcular_posiciones_planetarias(dia_juliano, latitud, resultado_casas["_armc"])

    dignidades = calcular_dignidades_de_carta(posiciones)
    elementos = calcular_elementos_y_modalidades(posiciones)

    return {"dignidades": dignidades, "elementos_y_modalidades": elementos}

    