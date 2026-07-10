from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from app.core.database import Base


class CartaNatalGuardada(Base):
    """
    Guarda el resultado completo de una carta natal ya generada:
    cálculo astronómico + aspectos + interpretación IA.

    Se identifica de forma única por los 3 datos de nacimiento
    (fecha_hora_local, latitud, longitud). Si alguien vuelve a pedir
    la misma carta, se sirve este registro en vez de recalcular todo
    y volver a llamar a Claude — más rápido y con texto consistente.
    """

    __tablename__ = "cartas_natales"

    id = Column(Integer, primary_key=True, index=True)

    # Datos de nacimiento (usados para identificar si la carta ya existe)
    fecha_hora_local = Column(DateTime, nullable=False, index=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)

    # Resultado completo, guardado como JSON serializado (texto plano).
    # Se deserializa con json.loads() al leer, y se serializa con
    # json.dumps() al guardar. Evita crear una tabla por cada planeta/aspecto.
    calculo_json = Column(Text, nullable=False)
    interpretacion_json = Column(Text, nullable=False)

    fecha_generacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))