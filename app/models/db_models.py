from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
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


class ProductoConfig(Base):
    """
    Configuración de un producto/reporte generable a partir de una carta ya
    calculada: qué secciones tiene, qué prompt usar, y qué parte del cálculo
    le interesa (vía criterios_json, consumido por
    domain.foco_astrologico_service.extraer_foco). Existe para poder dar de
    alta un producto nuevo (ej. "Reporte de vocación", "Mini reporte de amor")
    declarándolo como datos en vez de escribir código Python por cada uno —
    generacion_producto_service.py lee esta fila para saber qué pedirle a
    Claude y cómo validar la respuesta (secciones_json arma el schema
    dinámico vía domain.schema_dinamico_service.construir_schema).
    """

    __tablename__ = "producto_configs"

    codigo = Column(String, primary_key=True)  # identificador estable, ej. "reporte_vocacion"
    nombre = Column(String, nullable=False)  # nombre legible para el panel de admin

    system_prompt = Column(Text, nullable=False)
    instrucciones_usuario_template = Column(Text, nullable=False)  # se arma con .format(**inputs_adicionales, foco_json=...)

    # Cómo recortar el cálculo de la carta para este producto (ver
    # domain.foco_astrologico_service.extraer_foco). Alternativos entre sí:
    # criterios_json es un único set de criterios fijo; temas_a_criterios_json
    # mapea un input del usuario ("tema") a distintos criterios posibles según
    # lo que pida. Si ninguno de los dos está seteado, el producto usa el
    # cálculo completo de la carta (extraer_foco con criterios vacíos).
    criterios_json = Column(Text, nullable=True)
    temas_a_criterios_json = Column(Text, nullable=True)

    secciones_json = Column(Text, nullable=False)  # ver domain.schema_dinamico_service.construir_schema
    inputs_requeridos_json = Column(Text, nullable=False)  # lista de claves que inputs_adicionales debe traer

    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProductoGenerado(Base):
    """
    Una instancia generada de un ProductoConfig para una carta específica
    (ej. "el reporte de vocación de Juan"). Distinto de CartaNatalGuardada:
    una misma carta puede tener muchos ProductoGenerado (uno por producto
    comprado), cada uno con su propio ciclo de vida de aprobación/envío.

    Valores válidos de `estado` y su secuencia esperada:
        pendiente -> generando -> generado -> (editado)* -> aprobado -> enviado

    "fallido" es un estado terminal alternativo: se llega a él si la llamada
    a Claude devuelve "_validation_error" en vez de contenido válido (mismo
    patrón que las 5 llamadas de interpretation_*.py, vía
    interpretation_common._parsear_respuesta). Un ProductoGenerado en estado
    "fallido" puede reintentarse llamando de nuevo a generar_producto.
    """

    __tablename__ = "productos_generados"

    id = Column(Integer, primary_key=True, index=True)
    carta_id = Column(Integer, ForeignKey("cartas_natales.id"), nullable=False)
    producto_codigo = Column(String, ForeignKey("producto_configs.codigo"), nullable=False)

    inputs_json = Column(Text, nullable=False)  # inputs_adicionales con los que se generó (o se va a generar)
    contenido_json = Column(Text, nullable=True)  # resultado validado de Claude, nulo hasta "generado"

    estado = Column(String, nullable=False, default="pendiente")

    # Token opaco único para acceso sin login, mismo patrón que
    # CartaNatalGuardada.token — nulo hasta que se aprueba manualmente.
    token = Column(String, nullable=True, unique=True, index=True)

    fecha_generacion = Column(DateTime, nullable=True)
    fecha_aprobacion = Column(DateTime, nullable=True)
    fecha_envio = Column(DateTime, nullable=True)
