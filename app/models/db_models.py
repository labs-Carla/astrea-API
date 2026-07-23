from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime, timezone
from app.core.database import Base


class CartaNatalGuardada(Base):
    """
    Guarda el resultado de una carta natal: cálculo astronómico siempre,
    y de forma independiente el resumen gratuito y/o la interpretación premium.

    Estado de la carta según qué columnas tienen datos:
    - calculo_json + resumen_json: generó el flujo gratuito, aún no compró el premium.
    - + interpretacion_json: ya compró el premium (interpretación completa generada).
    - + token + enviado=True: fue aprobada manualmente y el cliente ya recibió
      el correo con el link de acceso a su lectura.

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

    # Datos de la compra premium (llenados cuando el cliente pasa por
    # formulario.html tras comprar en Hotmart). Nulos si la carta solo
    # pasó por el flujo gratuito.
    nombre_reporte = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)

    # Token opaco único para acceso sin login (patrón tipo Notion/Loom).
    # Nulo hasta que se aprueba manualmente el envío.
    token = Column(String, nullable=True, unique=True, index=True)
    enviado = Column(Boolean, nullable=False, default=False)
    fecha_envio = Column(DateTime, nullable=True)

    fecha_generacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))