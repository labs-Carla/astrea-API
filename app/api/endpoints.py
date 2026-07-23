import json
from fastapi import Request
from app.core.limiter import limiter
from fastapi import APIRouter, HTTPException
from app.models.schemas import DatosNacimiento, DatosCompra
from app.services.time_service import calcular_hora_utc, calcular_dia_juliano
from app.services.astro_service import calcular_casas, calcular_posiciones_planetarias
from fastapi.responses import HTMLResponse
from app.services.report_service import generar_html_reporte, construir_contexto
from fastapi.responses import Response
from app.services.pdf_service import generar_pdf_desde_html
from app.services.interpretation_service import interpretar_carta_completa
from app.services.resumen_deterministico_service import generar_resumen_deterministico
from app.services.aspectos_service import calcular_todos_los_aspectos
from app.core.admin_auth import verificar_admin_secret

from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.services.persistence_service import (
    buscar_carta_existente,
    guardar_resumen,
    guardar_carta_completa,
    actualizar_con_interpretacion,
    actualizar_datos_compra,
    listar_pendientes_de_aprobacion,
    obtener_carta_por_id,
    deserializar_carta,
)

from app.services.dignidades_service import calcular_dignidades_de_carta, calcular_elementos_y_modalidades
from app.services.geocoding_service import geocodificar_ciudad



router = APIRouter()


def _calcular_todo(datos: DatosNacimiento, latitud: float, longitud: float) -> dict:
    """
    Ejecuta el cálculo astronómico completo (posiciones, casas, aspectos,
    dignidades, elementos) a partir de coordenadas ya geocodificadas.
    Centraliza esta lógica para no repetirla entre /resumen y /pdf.
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


def _metadata_base(datos: DatosNacimiento, latitud: float, longitud: float, fecha_hora_utc: str) -> dict:
    return {
        "nombre": datos.nombre,
        "fecha_hora_local": datos.fecha_hora_local.isoformat(),
        "fecha_hora_utc": fecha_hora_utc,
        "ciudad": datos.ciudad,
        "pais": datos.pais,
        "latitud": latitud,
        "longitud": longitud,
    }

@router.post("/carta-natal/resumen")
@limiter.limit("5/minute")
async def generar_resumen_gratuito(request:Request, datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        carta_existente = buscar_carta_existente(db, datos.fecha_hora_local, latitud, longitud)

        if carta_existente is not None:
            calculo, resumen, _ = deserializar_carta(carta_existente)
            if resumen is None:
                # Existe la fila (probablemente ya compró premium) pero nunca pasó
                # por el flujo gratis: generamos el resumen reutilizando el calculo ya guardado.
                resumen = generar_resumen_deterministico(calculo)
                carta_existente.resumen_json = json.dumps(resumen)
                db.commit()
        else:
            resultado = _calcular_todo(datos, latitud, longitud)
            calculo = resultado["calculo"]
            resumen = generar_resumen_deterministico(calculo)
            guardar_resumen(db, datos.fecha_hora_local, latitud, longitud, calculo, resumen)

        metadata = _metadata_base(datos, latitud, longitud, calculo.get("fecha_hora_utc", ""))

        return {
            "metadata": metadata,
            "calculo": calculo,
            "resumen": resumen,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/carta-natal/html", response_class=HTMLResponse)
def generar_carta_natal_html(datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        carta_existente = buscar_carta_existente(db, datos.fecha_hora_local, latitud, longitud)

        if carta_existente is None:
            raise HTTPException(
                status_code=404,
                detail="Esta carta no ha sido generada todavía. Usa /carta-natal/pdf primero.",
            )

        calculo, _, interpretacion = deserializar_carta(carta_existente)

        if interpretacion is None:
            raise HTTPException(
                status_code=404,
                detail="Esta carta solo tiene el resumen gratuito generado. Usa /carta-natal/pdf para el reporte completo.",
            )

        metadata = _metadata_base(datos, latitud, longitud, calculo.get("fecha_hora_utc", ""))
        html = generar_html_reporte(metadata, calculo, interpretacion)
        return HTMLResponse(content=html)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/carta-natal/data")
def generar_carta_natal_data(datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        carta_existente = buscar_carta_existente(db, datos.fecha_hora_local, latitud, longitud)

        if carta_existente is None:
            raise HTTPException(
                status_code=404,
                detail="Esta carta no ha sido generada todavía. Usa /carta-natal/pdf primero.",
            )

        calculo, _, interpretacion = deserializar_carta(carta_existente)

        if interpretacion is None:
            raise HTTPException(
                status_code=404,
                detail="Esta carta solo tiene el resumen gratuito generado. Usa /carta-natal/pdf para el reporte completo.",
            )

        metadata = _metadata_base(datos, latitud, longitud, calculo.get("fecha_hora_utc", ""))
        return construir_contexto(metadata, calculo, interpretacion)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/carta-natal/pdf")
async def generar_carta_natal_pdf(datos: DatosNacimiento, db: Session = Depends(get_db)):
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        carta_existente = buscar_carta_existente(db, datos.fecha_hora_local, latitud, longitud)

        if carta_existente is not None:
            calculo, _, interpretacion = deserializar_carta(carta_existente)

            if interpretacion is None:
                # Ya generó su resumen gratis: reutilizamos el calculo, solo falta
                # la interpretacion completa (evita recalcular Swiss Ephemeris).
                interpretacion = await interpretar_carta_completa(calculo)
                carta_existente = actualizar_con_interpretacion(db, carta_existente, interpretacion)
        else:
            resultado = _calcular_todo(datos, latitud, longitud)
            calculo = resultado["calculo"]
            interpretacion = await interpretar_carta_completa(calculo)
            guardar_carta_completa(db, datos.fecha_hora_local, latitud, longitud, calculo, interpretacion)

        metadata = _metadata_base(datos, latitud, longitud, calculo.get("fecha_hora_utc", ""))
        html = generar_html_reporte(metadata, calculo, interpretacion)
        pdf_bytes = generar_pdf_desde_html(html)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=carta_natal.pdf"},
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/carta-natal/compra")
async def procesar_compra(datos: DatosCompra, db: Session = Depends(get_db)):
    """
    Recibe los datos enviados desde gracias.html tras una compra en Hotmart.
    Dispara el calculo astronomico y la interpretacion completa via IA (si no
    existian ya), y guarda nombre_reporte + email para revision manual antes
    de aprobar el envio del link de acceso al cliente.
    """
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        carta_existente = buscar_carta_existente(db, datos.fecha_hora_local, latitud, longitud)

        if carta_existente is not None:
            calculo, _, interpretacion = deserializar_carta(carta_existente)

            if interpretacion is None:
                interpretacion = await interpretar_carta_completa(calculo)
                carta_existente = actualizar_con_interpretacion(db, carta_existente, interpretacion)

            carta_existente = actualizar_datos_compra(db, carta_existente, datos.nombre, datos.email)
        else:
            resultado = _calcular_todo(datos, latitud, longitud)
            calculo = resultado["calculo"]
            interpretacion = await interpretar_carta_completa(calculo)
            guardar_carta_completa(
                db, datos.fecha_hora_local, latitud, longitud, calculo, interpretacion,
                nombre_reporte=datos.nombre, email=datos.email,
            )

        return {"status": "recibido", "mensaje": "Datos guardados, tu lectura esta siendo preparada."}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/pendientes", dependencies=[Depends(verificar_admin_secret)])
def listar_pendientes(db: Session = Depends(get_db)):
    """
    Devuelve la lista de cartas pendientes de revision/aprobacion: las que
    vienen del flujo de compra (tienen email) y aun no se les envio el link.
    """
    pendientes = listar_pendientes_de_aprobacion(db)
    return [
        {
            "id": carta.id,
            "nombre_reporte": carta.nombre_reporte,
            "email": carta.email,
            "fecha_hora_local": carta.fecha_hora_local.isoformat(),
            "fecha_generacion": carta.fecha_generacion.isoformat() if carta.fecha_generacion else None,
        }
        for carta in pendientes
    ]

@router.get("/admin/carta/{carta_id}", dependencies=[Depends(verificar_admin_secret)])
def ver_detalle_carta(carta_id: int, db: Session = Depends(get_db)):
    """
    Devuelve el detalle completo de una carta (calculo + interpretacion) para
    que el admin revise la calidad antes de aprobar el envio al cliente.
    """
    carta = obtener_carta_por_id(db, carta_id)

    if carta is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    calculo, _, interpretacion = deserializar_carta(carta)

    if interpretacion is None:
        raise HTTPException(
            status_code=409,
            detail="Esta carta aun no tiene interpretacion completa generada.",
        )

    return {
        "id": carta.id,
        "nombre_reporte": carta.nombre_reporte,
        "email": carta.email,
        "enviado": carta.enviado,
        "calculo": calculo,
        "interpretacion": interpretacion,
    }


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

    