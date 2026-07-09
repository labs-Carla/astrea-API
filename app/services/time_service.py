from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
import swisseph as swe

tf = TimezoneFinder()


def obtener_zona_horaria(latitud: float, longitud: float) -> str:
    """
    Deduce el nombre de zona horaria IANA (ej. 'America/Bogota')
    a partir de coordenadas geográficas.
    """
    zona = tf.timezone_at(lat=latitud, lng=longitud)
    if zona is None:
        raise ValueError(f"No se pudo determinar zona horaria para lat={latitud}, lon={longitud}")
    return zona


def calcular_hora_utc(fecha_local: datetime, latitud: float, longitud: float) -> datetime:
    """
    Convierte una fecha/hora local (naive, sin tzinfo) a UTC,
    usando la zona horaria histórica real del punto geográfico.
    """
    nombre_zona = obtener_zona_horaria(latitud, longitud)
    zona_local = ZoneInfo(nombre_zona)

    fecha_con_zona = fecha_local.replace(tzinfo=zona_local)
    fecha_utc = fecha_con_zona.astimezone(timezone.utc)

    return fecha_utc


def calcular_dia_juliano(fecha_utc: datetime) -> float:
    """
    Calcula el Día Juliano (UT) requerido por Swiss Ephemeris,
    a partir de una fecha/hora ya en UTC.
    """
    hora_decimal = (
        fecha_utc.hour
        + fecha_utc.minute / 60
        + fecha_utc.second / 3600
    )

    dia_juliano = swe.julday(
        fecha_utc.year,
        fecha_utc.month,
        fecha_utc.day,
        hora_decimal
    )

    return dia_juliano