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
    areas_de_vida_json = Column(Text, nullable=True)  # segunda llamada a Claude: vocacion, dinero, amor, etc.
    transitos_json = Column(Text, nullable=True)  # tercera llamada a Claude: clima energetico y proximos meses, foto fija del dia de aprobacion

    # Datos de la compra premium (llenados cuando el cliente pasa por
    # formulario.html tras comprar en Hotmart). Nulos si la carta solo
    # pasó por el flujo gratuito.
    nombre_reporte = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    fecha_solicitud_compra = Column(DateTime, nullable=True)  # cuando se envio el formulario de gracias.html, distinto de fecha_generacion (calculo) y fecha_envio (aprobacion)

    genero = Column(String, nullable=True)  # "femenino"/"masculino", para concordancia de genero en espanol en ambas llamadas a Claude

    # Token opaco único para acceso sin login (patrón tipo Notion/Loom).
    # Nulo hasta que se aprueba manualmente el envío.
    token = Column(String, nullable=True, unique=True, index=True)
    enviado = Column(Boolean, nullable=False, default=False)
    fecha_envio = Column(DateTime, nullable=True)

    fecha_generacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class HoroscopoGenerado(Base):
    """
    Guarda los horoscopos genericos (no personalizados) generados diaria o
    semanalmente para los 12 signos. Distinto de CartaNatalGuardada, que es
    por cliente individual.
    """
    __tablename__ = "horoscopos_generados"

    id = Column(Integer, primary_key=True, index=True)
    cadencia = Column(String, nullable=False, index=True)  # 'diario' o 'semanal'
    fecha = Column(DateTime, nullable=False, index=True)  # dia (o inicio de semana) al que corresponde
    contenido_json = Column(Text, nullable=False)  # el dict de HoroscoposDelDia/DeLaSemana serializado
    fecha_generacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
