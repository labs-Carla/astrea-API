import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.db_models import CartaNatalGuardada


def buscar_carta_existente(
    db: Session, fecha_hora_local: datetime, latitud: float, longitud: float
) -> CartaNatalGuardada | None:
    """
    Busca si ya existe una carta generada con estos datos exactos de nacimiento.
    Retorna el registro si existe, o None si no se ha generado antes.
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


def guardar_carta(
    db: Session,
    fecha_hora_local: datetime,
    latitud: float,
    longitud: float,
    calculo: dict,
    interpretacion: dict,
) -> CartaNatalGuardada:
    """
    Guarda el resultado completo de una carta recién generada
    (cálculo astronómico + aspectos + interpretación IA).
    """
    nueva_carta = CartaNatalGuardada(
        fecha_hora_local=fecha_hora_local,
        latitud=latitud,
        longitud=longitud,
        calculo_json=json.dumps(calculo),
        interpretacion_json=json.dumps(interpretacion),
    )
    db.add(nueva_carta)
    db.commit()
    db.refresh(nueva_carta)
    return nueva_carta


def deserializar_carta(carta: CartaNatalGuardada) -> tuple[dict, dict]:
    """
    Convierte los campos JSON guardados como texto de vuelta a dicts de Python,
    listos para usar en report_service.py igual que si vinieran recién calculados.
    """
    calculo = json.loads(carta.calculo_json)
    interpretacion = json.loads(carta.interpretacion_json)
    return calculo, interpretacion