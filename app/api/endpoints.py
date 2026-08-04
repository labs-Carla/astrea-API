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
from app.services.interpretation_service import interpretar_carta_completa, interpretar_areas_de_vida, interpretar_transitos,generar_horoscopos
from app.services.transitos_service import calcular_transitos_actuales, calcular_transitos_por_signo
from app.services.resumen_deterministico_service import generar_resumen_deterministico
from app.services.aspectos_service import calcular_todos_los_aspectos
from app.core.admin_auth import verificar_admin_secret
from pydantic import BaseModel

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
    aprobar_y_generar_token,
    buscar_carta_por_token,
    actualizar_genero,
    guardar_areas_de_vida,
    obtener_areas_de_vida,
    guardar_transitos,
    obtener_transitos,
    deserializar_carta,
    guardar_horoscopo,
    obtener_horoscopo_mas_reciente
)

from app.services.dignidades_service import calcular_dignidades_de_carta, calcular_elementos_y_modalidades
from app.services.geocoding_service import geocodificar_ciudad
from app.services.time_service import calcular_dia_juliano
from datetime import datetime, timezone



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

def _iso_utc(valor):
    """Serializa un datetime naive (guardado como UTC) a ISO string con
    sufijo Z explicito, para que el frontend lo interprete correctamente
    como UTC y no como hora local del navegador."""
    return valor.isoformat() + "Z" if valor else None


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
            resultado = _calcular_todo(datos, latitud, longitud)
            calculo = resultado["calculo"]
            guardar_carta_completa(
                db, datos.fecha_hora_local, latitud, longitud, calculo, interpretacion=None,
                nombre_reporte=datos.nombre, email=datos.email,
            )

        return {"status": "recibido", "mensaje": "Datos guardados, tu lectura esta siendo preparada."}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/pendientes", dependencies=[Depends(verificar_admin_secret)])
def listar_pendientes(db: Session = Depends(get_db)):
    pendientes = listar_pendientes_de_aprobacion(db)
    return [
        {
            "id": carta.id,
            "nombre_reporte": carta.nombre_reporte,
            "email": carta.email,
            "fecha_hora_local": carta.fecha_hora_local.isoformat(),
            "fecha_generacion": _iso_utc(carta.fecha_generacion),
            "fecha_solicitud_compra": _iso_utc(carta.fecha_solicitud_compra),
        }
        for carta in pendientes
    ]

@router.get("/admin/carta/{carta_id}", dependencies=[Depends(verificar_admin_secret)])
def ver_detalle_carta(carta_id: int, db: Session = Depends(get_db)):
    """
    Devuelve el detalle completo de una carta (calculo + interpretacion +
    areas_de_vida + transitos, si existen) para que el admin revise la
    calidad antes de aprobar el envio al cliente.
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
        "genero": carta.genero,
        "calculo": calculo,
        "interpretacion": interpretacion,
        "areas_de_vida": obtener_areas_de_vida(carta),
        "transitos": obtener_transitos(carta),
    }

@router.post("/admin/aprobar/{carta_id}", dependencies=[Depends(verificar_admin_secret)])
def aprobar_envio(carta_id: int, db: Session = Depends(get_db)):
    """
    Aprueba manualmente una carta revisada: genera el token de acceso y la
    marca como enviada. Por ahora NO envia el correo automaticamente (Gmail
    SMTP aun no esta configurado) — devuelve el link para que el admin lo
    envie manualmente al cliente.
    """
    carta = obtener_carta_por_id(db, carta_id)

    if carta is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    if carta.interpretacion_json is None:
        raise HTTPException(
            status_code=409,
            detail="Esta carta no tiene interpretacion completa. Usa /admin/generar-interpretacion primero.",
        )

    if carta.enviado:
        return {
            "status": "ya_aprobada",
            "link": f"https://astrea-charts.site/r/{carta.token}",
        }

    carta = aprobar_y_generar_token(db, carta)

    return {
        "status": "aprobada",
        "link": f"https://astrea-charts.site/r/{carta.token}",
    }

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

class ConversionAPremium(BaseModel):
    nombre_reporte: str | None = None
    email: str | None = None
    genero: str | None = None
    forzar: bool = False


@router.post("/admin/generar-interpretacion/{carta_id}", dependencies=[Depends(verificar_admin_secret)])
async def generar_interpretacion_admin(
    carta_id: int, datos: ConversionAPremium, db: Session = Depends(get_db)
):
    """
    Genera la interpretacion completa via IA para una carta que ya existe,
    reutilizando el calculo_json ya guardado. Opcionalmente completa
    nombre_reporte/email/genero. Si forzar=True, regenera aunque ya exista
    interpretacion (util para corregir concordancia de genero en cartas
    generadas antes de que este campo existiera).
    """
    carta = obtener_carta_por_id(db, carta_id)

    if carta is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    if datos.nombre_reporte and datos.email:
        carta = actualizar_datos_compra(db, carta, datos.nombre_reporte, datos.email)

    if datos.genero:
        carta = actualizar_genero(db, carta, datos.genero)

    calculo, _, interpretacion = deserializar_carta(carta)

    if interpretacion is not None and not datos.forzar:
        return {"status": "ya_existia", "mensaje": "Esta carta ya tenia interpretacion generada."}

    interpretacion = await interpretar_carta_completa(calculo, carta.genero)
    actualizar_con_interpretacion(db, carta, interpretacion)

    return {"status": "generada", "mensaje": "Interpretacion generada correctamente."}


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

class GenerarAreasDeVidaRequest(BaseModel):
    genero: str | None = None
    forzar: bool = False


@router.post("/admin/generar-areas-de-vida/{carta_id}", dependencies=[Depends(verificar_admin_secret)])
async def generar_areas_de_vida_admin(
    carta_id: int, datos: GenerarAreasDeVidaRequest, db: Session = Depends(get_db)
):
    """
    Genera la segunda llamada a Claude (vocacion, dinero, amor, herida/don,
    aspectos interpretados, plan de accion, brujula) para una carta que ya
    tiene el calculo_json guardado. Opcionalmente actualiza el genero de la
    carta antes de generar. Si forzar=True, regenera aunque ya existan
    areas de vida validas.
    """
    carta = obtener_carta_por_id(db, carta_id)

    if carta is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    if datos.genero:
        carta = actualizar_genero(db, carta, datos.genero)

    areas_existentes = obtener_areas_de_vida(carta)
    if areas_existentes is not None and "_validation_error" not in areas_existentes and not datos.forzar:
        return {"status": "ya_existia", "mensaje": "Esta carta ya tenia areas de vida generadas."}

    calculo, _, _ = deserializar_carta(carta)
    areas_de_vida = await interpretar_areas_de_vida(calculo, carta.genero)
    guardar_areas_de_vida(db, carta, areas_de_vida)

    return {"status": "generada", "mensaje": "Areas de vida generadas correctamente."}

class GenerarTransitosRequest(BaseModel):
    genero: str | None = None
    forzar: bool = False


@router.post("/admin/generar-transitos/{carta_id}", dependencies=[Depends(verificar_admin_secret)])
async def generar_transitos_admin(
    carta_id: int, datos: GenerarTransitosRequest, db: Session = Depends(get_db)
):
    """
    Calcula el clima energetico actual (transitos de hoy vs carta natal) y
    genera la tercera llamada a Claude (clima energetico + proximos meses).
    Es una foto fija del momento de aprobacion, no se actualiza sola despues.
    """
    carta = obtener_carta_por_id(db, carta_id)

    if carta is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    if datos.genero:
        carta = actualizar_genero(db, carta, datos.genero)

    transitos_existentes = obtener_transitos(carta)
    if transitos_existentes is not None and "_validation_error" not in transitos_existentes and not datos.forzar:
        return {"status": "ya_existia", "mensaje": "Esta carta ya tenia transitos generados."}

    calculo, _, _ = deserializar_carta(carta)
    transitos_calculados = calcular_transitos_actuales(calculo)
    interpretacion_transitos = await interpretar_transitos(calculo, transitos_calculados, carta.genero)
    guardar_transitos(db, carta, interpretacion_transitos)

    return {"status": "generada", "mensaje": "Transitos generados correctamente."}

@router.get("/admin/enviadas", dependencies=[Depends(verificar_admin_secret)])
def listar_enviadas(db: Session = Depends(get_db)):
    from app.models.db_models import CartaNatalGuardada

    enviadas = (
        db.query(CartaNatalGuardada)
        .filter(CartaNatalGuardada.enviado.is_(True))
        .order_by(CartaNatalGuardada.fecha_envio.desc())
        .all()
    )

    return [
        {
            "id": carta.id,
            "nombre_reporte": carta.nombre_reporte,
            "email": carta.email,
            "fecha_hora_local": carta.fecha_hora_local.isoformat(),
            "fecha_envio": _iso_utc(carta.fecha_envio),
            "token": carta.token,
        }
        for carta in enviadas
    ]

@router.post("/admin/generar-horoscopos/{cadencia}", dependencies=[Depends(verificar_admin_secret)])
async def generar_horoscopos_admin(cadencia: str, db: Session = Depends(get_db)):
    """
    Genera y guarda los horoscopos genericos (diario o semanal) para los
    12 signos, basados en los transitos de hoy. cadencia debe ser 'diario'
    o 'semanal'.
    """
    if cadencia not in ("diario", "semanal"):
        raise HTTPException(status_code=400, detail="cadencia debe ser 'diario' o 'semanal'.")

    ahora_utc = datetime.now(timezone.utc)
    dia_juliano_hoy = calcular_dia_juliano(ahora_utc)

    transitos_por_signo = calcular_transitos_por_signo(dia_juliano_hoy)
    contenido = await generar_horoscopos(transitos_por_signo, cadencia)

    if "_validation_error" in contenido:
        raise HTTPException(status_code=502, detail=f"Error al generar: {contenido['_validation_error']}")

    guardar_horoscopo(db, cadencia, ahora_utc, contenido)

    return {"status": "generado", "cadencia": cadencia}


@router.get("/horoscopos/{cadencia}")
def obtener_horoscopos_publico(cadencia: str, db: Session = Depends(get_db)):
    """
    Endpoint publico (sin auth) que devuelve el horoscopo mas reciente de
    la cadencia pedida. Consumido por el frontend publico de horoscopos.
    """
    if cadencia not in ("diario", "semanal"):
        raise HTTPException(status_code=400, detail="cadencia debe ser 'diario' o 'semanal'.")

    horoscopo = obtener_horoscopo_mas_reciente(db, cadencia)

    if horoscopo is None:
        raise HTTPException(status_code=404, detail="Aun no hay horoscopos generados para esta cadencia.")

    return {
        "cadencia": horoscopo.cadencia,
        "fecha": horoscopo.fecha.isoformat() + "Z",
        "contenido": json.loads(horoscopo.contenido_json),
    }