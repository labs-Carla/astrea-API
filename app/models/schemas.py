from pydantic import BaseModel, Field
from datetime import datetime


class DatosNacimiento(BaseModel):
    fecha_hora_local: datetime = Field(
        ...,
        description="Fecha y hora local de nacimiento, sin zona horaria. Ej: 2000-08-25T14:50:00"
    )
    latitud: float = Field(..., ge=-90, le=90, description="Latitud en grados decimales")
    longitud: float = Field(..., ge=-180, le=180, description="Longitud en grados decimales")


class RespuestaCartaNatal(BaseModel):
    metadata: dict
    calculo: dict


class CartaEnUnaMirada(BaseModel):
    """
    Resumen ejecutivo de la carta: página breve pensada para que el lector
    entienda el eje principal de su carta en menos de dos minutos, sin
    repetir el desarrollo que aparece más adelante en overview/capítulos.
    """
    esencia: str = Field(
        ..., min_length=10, max_length=140,
        description="3-4 conceptos breves (una o dos palabras cada uno) que definan el eje principal de la carta, ej. 'Analítica · Transformadora · Sensible'"
    )
    talentos: list[str] = Field(
        ..., min_length=3, max_length=4,
        description="3-4 fortalezas breves (pocas palabras cada una), derivadas de la carta"
    )
    desafios: list[str] = Field(
        ..., min_length=3, max_length=4,
        description="3-4 desafíos breves (pocas palabras cada uno), derivados de la carta"
    )
    mision: str = Field(
        ..., min_length=80, max_length=900,
        description="Párrafo breve que sintetiza el camino evolutivo de la carta"
    )


class InterpretacionCompleta(BaseModel):
    carta_en_una_mirada: CartaEnUnaMirada = Field(
        ..., description="Resumen ejecutivo de la carta, para la página inicial 'Tu carta en una mirada'"
    )
    overview: str = Field(..., min_length=100, description="Resumen general que amarra toda la carta")
    lectura_elementos_dignidades: str = Field(
        ..., min_length=80,
        description="Interpretación del patrón compuesto por el elemento/modalidad dominante junto con las dignidades esenciales presentes en la carta"
    )
    sol: str = Field(..., min_length=50)
    luna: str = Field(..., min_length=50)
    mercurio: str = Field(..., min_length=50)
    venus: str = Field(..., min_length=50)
    marte: str = Field(..., min_length=50)
    jupiter: str = Field(..., min_length=50)
    saturno: str = Field(..., min_length=50)
    urano: str = Field(..., min_length=50)
    neptuno: str = Field(..., min_length=50)
    pluton: str = Field(..., min_length=50)
    nodo_norte: str = Field(..., min_length=50)
    quiron: str = Field(..., min_length=50)
    ascendente: str = Field(..., min_length=50)
    medio_cielo: str = Field(..., min_length=50)
    conclusion: str = Field(..., min_length=80, description="Cierre que integra los temas principales de la carta")
    frase_de_cierre: str = Field(
        ..., min_length=20, max_length=200,
        description="Frase breve y memorable para la última página del reporte, que sintetiza el espíritu de la carta sin caer en clichés"
    )