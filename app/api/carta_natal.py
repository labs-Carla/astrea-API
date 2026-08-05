import json
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.database import get_db
from app.models.schemas import DatosNacimiento, DatosCompra
from app.services.calculo_carta_service import calcular_todo
from app.services.report_service import generar_html_reporte, construir_contexto
from app.infrastructure.pdf_service import generar_pdf_desde_html
from app.services.interpretation_carta_completa import interpretar_carta_completa
from app.domain.resumen_deterministico_service import generar_resumen_deterministico
from app.infrastructure.geocoding_service import geocodificar_ciudad
from app.infrastructure.persistence_service import (
    buscar_carta_existente,
    guardar_resumen,
    guardar_carta_completa,
    actualizar_con_interpretacion,
    actualizar_datos_compra,
    buscar_carta_por_token,
    obtener_areas_de_vida,
    obtener_transitos,
    deserializar_carta,
)

router = APIRouter()


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
async def generar_resumen_gratuito(request: Request, datos: DatosNacimiento, db: Session = Depends(get_db)):
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
            resultado = calcular_todo(datos, latitud, longitud)
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
@limiter.limit("5/minute")
def generar_carta_natal_html(request: Request, datos: DatosNacimiento, db: Session = Depends(get_db)):
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
@limiter.limit("5/minute")
def generar_carta_natal_data(request: Request, datos: DatosNacimiento, db: Session = Depends(get_db)):
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
        contexto = construir_contexto(metadata, calculo, interpretacion)
        contexto["areas_de_vida"] = obtener_areas_de_vida(carta_existente)
        contexto["transitos"] = obtener_transitos(carta_existente)

        return contexto

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/carta-natal/pdf")
@limiter.limit("5/minute")
async def generar_carta_natal_pdf(request: Request, datos: DatosNacimiento, db: Session = Depends(get_db)):
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
            resultado = calcular_todo(datos, latitud, longitud)
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
@limiter.limit("5/minute")
async def procesar_compra(request: Request, datos: DatosCompra, db: Session = Depends(get_db)):
    """
    Recibe los datos enviados desde gracias.html tras una compra en Hotmart.
    Calcula la carta astronomica (Swiss Ephemeris, sin IA) y guarda
    nombre_reporte + email para que aparezca en el panel de admin. La
    interpretacion via Claude se genera manualmente despues desde el panel,
    no automaticamente aqui.
    """
    try:
        latitud, longitud = geocodificar_ciudad(datos.ciudad, datos.pais)

        carta_existente = buscar_carta_existente(db, datos.fecha_hora_local, latitud, longitud)

        if carta_existente is not None:
            carta_existente = actualizar_datos_compra(db, carta_existente, datos.nombre, datos.email)
        else:
            resultado = calcular_todo(datos, latitud, longitud)
            calculo = resultado["calculo"]
            guardar_carta_completa(
                db, datos.fecha_hora_local, latitud, longitud, calculo, interpretacion=None,
                nombre_reporte=datos.nombre, email=datos.email,
            )

        return {"status": "recibido", "mensaje": "Datos guardados, tu lectura esta siendo preparada."}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/carta-natal/token/{token}")
def obtener_carta_por_token(token: str, db: Session = Depends(get_db)):
    """
    Endpoint publico (sin login) que devuelve el JSON completo del reporte
    a partir de un token de acceso valido. Es el equivalente a /carta-natal/data
    pero identificando la carta por token en vez de fecha/ciudad/pais.
    """
    carta = buscar_carta_por_token(db, token)

    if carta is None:
        raise HTTPException(status_code=404, detail="Link invalido o expirado.")

    calculo, _, interpretacion = deserializar_carta(carta)

    if interpretacion is None:
        raise HTTPException(status_code=409, detail="Esta lectura aun no esta lista.")

    metadata = {
        "nombre": carta.nombre_reporte,
        "fecha_hora_local": carta.fecha_hora_local.isoformat(),
        "ciudad": None,
        "pais": None,
    }

    contexto = construir_contexto(metadata, calculo, interpretacion)
    contexto["areas_de_vida"] = obtener_areas_de_vida(carta)
    contexto["transitos"] = obtener_transitos(carta)
    return contexto
