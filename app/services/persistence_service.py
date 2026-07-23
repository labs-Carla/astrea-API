import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.db_models import CartaNatalGuardada


def buscar_carta_existente(
    db: Session, fecha_hora_local: datetime, latitud: float, longitud: float
) -> CartaNatalGuardada | None:
    """
    Busca si ya existe una carta generada con estos datos exactos de nacimiento,
    sin importar si tiene resumen, interpretacion completa, o ambos.
    """
    return (
        db.query(CartaNatalGuardada)
        .filter(
            CartaNatalGuardada.fecha_hora_local == fecha_hora_local,
            CartaNatalGuardada.latitud == latitud,
            CartaNatalGuardada.longitud == longitud,
        )
        .first()
    )


def guardar_resumen(
    db: Session,
    fecha_hora_local: datetime,
    latitud: float,
    longitud: float,
    calculo: dict,
    resumen: dict,
) -> CartaNatalGuardada:
    """
    Guarda una carta nueva generada por el flujo gratuito: calculo + resumen,
    sin interpretacion_json (queda None hasta que compre el premium).
    """
    nueva_carta = CartaNatalGuardada(
        fecha_hora_local=fecha_hora_local,
        latitud=latitud,
        longitud=longitud,
        calculo_json=json.dumps(calculo),
        resumen_json=json.dumps(resumen),
        interpretacion_json=None,
    )
    db.add(nueva_carta)
    db.commit()
    db.refresh(nueva_carta)
    return nueva_carta


def guardar_carta_completa(
    db: Session,
    fecha_hora_local: datetime,
    latitud: float,
    longitud: float,
    calculo: dict,
    interpretacion: dict,
    nombre_reporte: str | None = None,
    email: str | None = None,
) -> CartaNatalGuardada:
    """
    Guarda una carta nueva generada directamente en premium (sin haber pasado
    antes por el flujo gratuito): calculo + interpretacion, sin resumen_json.
    nombre_reporte y email se llenan cuando viene del flujo de compra
    (gracias.html); quedan None si es una prueba interna o el flujo gratuito.
    """
    nueva_carta = CartaNatalGuardada(
        fecha_hora_local=fecha_hora_local,
        latitud=latitud,
        longitud=longitud,
        calculo_json=json.dumps(calculo),
        interpretacion_json=json.dumps(interpretacion),
        resumen_json=None,
        nombre_reporte=nombre_reporte,
        email=email,
    )
    db.add(nueva_carta)
    db.commit()
    db.refresh(nueva_carta)
    return nueva_carta


def actualizar_con_interpretacion(
    db: Session, carta: CartaNatalGuardada, interpretacion: dict
) -> CartaNatalGuardada:
    """
    Actualiza una carta que ya existía (generada por el flujo gratuito) agregando
    la interpretacion_json del premium. El calculo_json existente se reutiliza tal cual
    — no se recalcula Swiss Ephemeris, porque ya se calculó cuando se generó el resumen.
    """
    carta.interpretacion_json = json.dumps(interpretacion)
    db.commit()
    db.refresh(carta)
    return carta


def actualizar_datos_compra(
    db: Session, carta: CartaNatalGuardada, nombre_reporte: str, email: str
) -> CartaNatalGuardada:
    """
    Actualiza una carta ya existente (típicamente generada antes por el flujo
    gratuito) con los datos de la compra premium: nombre_reporte y email,
    necesarios para el envío posterior del link de acceso.
    """
    carta.nombre_reporte = nombre_reporte
    carta.email = email
    db.commit()
    db.refresh(carta)
    return carta


def deserializar_carta(carta: CartaNatalGuardada) -> tuple[dict, dict | None, dict | None]:
    """
    Convierte los campos JSON guardados de vuelta a dicts de Python.
    Retorna (calculo, resumen, interpretacion) — resumen y/o interpretacion
    pueden ser None si esa etapa todavía no se generó para esta carta.
    """
    calculo = json.loads(carta.calculo_json)
    resumen = json.loads(carta.resumen_json) if carta.resumen_json else None
    interpretacion = json.loads(carta.interpretacion_json) if carta.interpretacion_json else None
    return calculo, resumen, interpretacion