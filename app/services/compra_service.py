from sqlalchemy.orm import Session

from app.models.db_models import CartaNatalGuardada
from app.models.schemas import DatosCompra
from app.services.calculo_carta_service import calcular_todo
from app.infrastructure.persistence_service import (
    buscar_carta_existente,
    guardar_carta_completa,
    actualizar_datos_compra,
)


def registrar_solicitud_compra(
    db: Session, datos: DatosCompra, latitud: float, longitud: float, pago_confirmado: bool
) -> CartaNatalGuardada:
    """
    Registra los datos de una compra premium sobre la carta (reutilizando el
    calculo si ya existia, ej. por el flujo gratuito). Sin IA: la
    interpretacion se genera despues desde el panel de admin.
    pago_confirmado=False para ordenes creadas antes de pagar en Hotmart
    (/carta-natal/orden); True para el flujo legado post-pago (/compra).
    """
    carta_existente = buscar_carta_existente(db, datos.fecha_hora_local, latitud, longitud)

    if carta_existente is not None:
        return actualizar_datos_compra(
            db, carta_existente, datos.nombre, datos.email, pago_confirmado=pago_confirmado
        )

    calculo = calcular_todo(datos, latitud, longitud)["calculo"]
    return guardar_carta_completa(
        db, datos.fecha_hora_local, latitud, longitud, calculo, interpretacion=None,
        nombre_reporte=datos.nombre, email=datos.email, pago_confirmado=pago_confirmado,
    )
