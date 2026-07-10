from fastapi import APIRouter, HTTPException
from app.models.schemas import DatosNacimiento
from app.services.time_service import calcular_hora_utc, calcular_dia_juliano
from app.services.astro_service import calcular_casas, calcular_posiciones_planetarias
from fastapi.responses import HTMLResponse
from app.services.report_service import generar_html_reporte
from fastapi.responses import Response
from app.services.pdf_service import generar_pdf_desde_html

from app.services.interpretation_service import interpretar_carta_completa

from app.services.aspectos_service import calcular_todos_los_aspectos

from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.services.persistence_service import buscar_carta_existente, guardar_carta, deserializar_carta



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
def generar_carta_natal_html(datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        carta_existente = buscar_carta_existente(
            db, datos.fecha_hora_local, datos.latitud, datos.longitud
        )

        if carta_existente is None:
            raise HTTPException(
                status_code=404,
                detail="Esta carta no ha sido generada todavía. Usa /carta-natal/pdf primero.",
            )

        calculo, interpretacion = deserializar_carta(carta_existente)
        metadata = {
            "fecha_hora_local": datos.fecha_hora_local.isoformat(),
            "fecha_hora_utc": calculo.get("fecha_hora_utc", ""),
            "latitud": datos.latitud,
            "longitud": datos.longitud,
        }

        html = generar_html_reporte(metadata, calculo, interpretacion)
        return HTMLResponse(content=html)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
@router.post("/carta-natal/pdf")
async def generar_carta_natal_pdf(datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        # Primero: ¿esta carta ya fue generada antes con estos datos exactos?
        carta_existente = buscar_carta_existente(
            db, datos.fecha_hora_local, datos.latitud, datos.longitud
        )

        if carta_existente is not None:
            calculo, interpretacion = deserializar_carta(carta_existente)
            metadata = {
                "fecha_hora_local": datos.fecha_hora_local.isoformat(),
                "fecha_hora_utc": calculo.get("fecha_hora_utc", ""),
                "latitud": datos.latitud,
                "longitud": datos.longitud,
            }
        else:
            fecha_utc = calcular_hora_utc(datos.fecha_hora_local, datos.latitud, datos.longitud)
            dia_juliano = calcular_dia_juliano(fecha_utc)

            resultado_casas = calcular_casas(dia_juliano, datos.latitud, datos.longitud)
            posiciones = calcular_posiciones_planetarias(
                dia_juliano, datos.latitud, resultado_casas["_armc"]
            )

            puntos_para_aspectos = {
                nombre: p["longitud_absoluta"] for nombre, p in posiciones.items()
            }
            puntos_para_aspectos["Ascendente"] = resultado_casas["puntos_angulares"]["Ascendente"]["longitud_absoluta"]
            puntos_para_aspectos["MedioCielo"] = resultado_casas["puntos_angulares"]["MedioCielo"]["longitud_absoluta"]

            aspectos = calcular_todos_los_aspectos(puntos_para_aspectos)

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
                "aspectos": aspectos,
                "fecha_hora_utc": fecha_utc.isoformat(),
            }

            interpretacion = await interpretar_carta_completa(calculo)

            guardar_carta(
                db, datos.fecha_hora_local, datos.latitud, datos.longitud, calculo, interpretacion
            )

        html = generar_html_reporte(metadata, calculo, interpretacion)
        pdf_bytes = await generar_pdf_desde_html(html)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=carta_natal.pdf"},
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test-interpretacion-completa")
async def test_interpretacion_completa(datos: DatosNacimiento):
    fecha_utc = calcular_hora_utc(datos.fecha_hora_local, datos.latitud, datos.longitud)
    dia_juliano = calcular_dia_juliano(fecha_utc)
    resultado_casas = calcular_casas(dia_juliano, datos.latitud, datos.longitud)
    posiciones = calcular_posiciones_planetarias(dia_juliano, datos.latitud, resultado_casas["_armc"])

    calculo = {
        "planetas": posiciones,
        "puntos_angulares": resultado_casas["puntos_angulares"],
    }

    interpretacion = await interpretar_carta_completa(calculo)
    return {"interpretacion": interpretacion}



@router.post("/test-aspectos")
def test_aspectos(datos: DatosNacimiento):
    fecha_utc = calcular_hora_utc(datos.fecha_hora_local, datos.latitud, datos.longitud)
    dia_juliano = calcular_dia_juliano(fecha_utc)
    resultado_casas = calcular_casas(dia_juliano, datos.latitud, datos.longitud)
    posiciones = calcular_posiciones_planetarias(dia_juliano, datos.latitud, resultado_casas["_armc"])

    # Armamos el dict de {nombre: grado_absoluto} con planetas + Ascendente + Medio Cielo
    puntos = {nombre: datos["longitud_absoluta"] for nombre, datos in posiciones.items()}
    puntos["Ascendente"] = resultado_casas["puntos_angulares"]["Ascendente"]["longitud_absoluta"]
    puntos["MedioCielo"] = resultado_casas["puntos_angulares"]["MedioCielo"]["longitud_absoluta"]

    aspectos = calcular_todos_los_aspectos(puntos)

    return {"total_aspectos": len(aspectos), "aspectos": aspectos}