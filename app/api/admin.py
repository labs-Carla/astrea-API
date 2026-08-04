from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.admin_auth import verificar_admin_secret
from app.services.time_service import calcular_dia_juliano
from app.services.interpretation_carta_completa import interpretar_carta_completa
from app.services.interpretation_areas_de_vida import interpretar_areas_de_vida
from app.services.interpretation_transitos import interpretar_transitos
from app.services.interpretation_horoscopos import generar_horoscopos
from app.services.transitos_service import calcular_transitos_actuales, calcular_transitos_por_signo
from app.infrastructure.persistence_service import (
    listar_pendientes_de_aprobacion,
    obtener_carta_por_id,
    aprobar_y_generar_token,
    actualizar_con_interpretacion,
    actualizar_datos_compra,
    actualizar_genero,
    guardar_areas_de_vida,
    obtener_areas_de_vida,
    guardar_transitos,
    obtener_transitos,
    deserializar_carta,
    guardar_horoscopo,
)

router = APIRouter()


def _iso_utc(valor):
    """Serializa un datetime naive (guardado como UTC) a ISO string con
    sufijo Z explicito, para que el frontend lo interprete correctamente
    como UTC y no como hora local del navegador."""
    return valor.isoformat() + "Z" if valor else None


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
