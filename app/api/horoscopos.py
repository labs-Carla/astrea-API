import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.persistence_service import obtener_horoscopo_mas_reciente

router = APIRouter()


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
