from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from app.core.database import Base


class CartaNatalGuardada(Base):
    """
    Guarda el resultado de una carta natal: cálculo astronómico siempre,
    y de forma independiente el resumen gratuito y/o la interpretación premium.

    Estado de la carta según qué columnas tienen datos:
    - calculo_json + resumen_json: generó el flujo gratuito, aún no compró el premium.
    - + interpretacion_json: ya compró el premium (interpretación completa generada).

    Se identifica de forma única por los 3 datos de nacimiento
    (fecha_hora_local, latitud, longitud). Si alguien que ya generó su
    resumen gratis vuelve a pedir el PDF premium, se reutiliza el calculo_json
    ya guardado en vez de recalcular Swiss Ephemeris desde cero.
    """

    __tablename__ = "cartas_natales"

    id = Column(Integer, primary_key=True, index=True)

    fecha_hora_local = Column(DateTime, nullable=False, index=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)

    calculo_json = Column(Text, nullable=False)
    resumen_json = Column(Text, nullable=True)
    interpretacion_json = Column(Text, nullable=True)  # antes era nullable=False

    fecha_generacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))