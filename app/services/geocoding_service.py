from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Nominatim (OpenStreetMap) exige un user_agent identificable en cada request,
# como parte de su política de uso justo. No puede ir vacío ni genérico.
_geolocalizador = Nominatim(user_agent="astrea-api-carta-natal")


def geocodificar_ciudad(ciudad: str, pais: str) -> tuple[float, float]:
    """
    Convierte un nombre de ciudad + país en coordenadas (latitud, longitud)
    usando Nominatim (OpenStreetMap). Pedir ciudad y país por separado reduce
    la ambigüedad de nombres de ciudad repetidos entre países (ej. "San José").

    Lanza ValueError si no se encuentra la ubicación, o si el servicio de
    geocodificación falla (timeout, error del servicio).
    """
    consulta = f"{ciudad}, {pais}"

    try:
        ubicacion = _geolocalizador.geocode(consulta)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        raise ValueError(
            f"No se pudo contactar el servicio de geocodificación para '{consulta}': {e}"
        )

    if ubicacion is None:
        raise ValueError(
            f"No se encontró la ubicación '{consulta}'. Verifica que la ciudad y el país estén escritos correctamente."
        )

    return ubicacion.latitude, ubicacion.longitude