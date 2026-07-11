from app.core.database import SessionLocal
from app.models.db_models import CartaNatalGuardada
from datetime import datetime

db = SessionLocal()
carta = db.query(CartaNatalGuardada).filter(
    CartaNatalGuardada.fecha_hora_local == datetime(2000, 8, 25, 14, 50, 0),
    CartaNatalGuardada.latitud == 4.5964,
    CartaNatalGuardada.longitud == -74.0721,
).first()

if carta:
    db.delete(carta)
    db.commit()
    print("Carta borrada, id:", carta.id)
else:
    print("No se encontró ninguna carta con esos datos.")

db.close()
