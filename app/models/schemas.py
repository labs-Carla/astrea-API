from pydantic import BaseModel, Field
from datetime import datetime


from pydantic import BaseModel, Field, field_validator
from datetime import datetime


from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import datetime


class DatosNacimiento(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150, description="...")
    fecha_hora_local: datetime = Field(..., description="...")
    ciudad: str = Field(..., min_length=2, max_length=150, description="...")
    pais: str = Field(..., min_length=2, max_length=150, description="...")

    @field_validator("fecha_hora_local")
    @classmethod
    def fecha_debe_ser_razonable(cls, valor: datetime) -> datetime:
        hoy = datetime.now()
        if valor.year < 1900:
            raise ValueError("La fecha de nacimiento no puede ser anterior al año 1900.")
        if valor > hoy:
            raise ValueError("La fecha de nacimiento no puede estar en el futuro.")
        return valor


class DatosCompra(DatosNacimiento):
    """
    Extiende DatosNacimiento agregando el email del comprador — usado en el
    flujo post-compra (gracias.html) para poder enviarle luego el correo
    con el link de acceso a su lectura, una vez se apruebe manualmente.
    """
    email: EmailStr = Field(..., description="Correo del comprador, para el envío posterior del link de acceso")


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


class InterpretacionResumen(BaseModel):
    resumen: str = Field(
        ...,
        min_length=1500,
        max_length=4500,
        description="Texto narrativo de 400-600 palabras que sintetiza el Big Three (Sol/Luna/Ascendente) "
                     "y 1-2 patrones destacados de la carta, como teaser del reporte completo"
    )
    
class AspectoInterpretado(BaseModel):
    punto_a: str = Field(..., description="Nombre del primer punto involucrado, ej. 'Sol'")
    aspecto: str = Field(..., description="Tipo de aspecto, ej. 'Trigono'")
    punto_b: str = Field(..., description="Nombre del segundo punto involucrado, ej. 'Luna'")
    interpretacion: str = Field(..., min_length=80, max_length=900, description="Interpretacion breve de que significa este aspecto especifico en la vida de la persona")

class PlanDeAccion(BaseModel):
    potencia: list[str] = Field(..., min_length=2, max_length=3, description="2-3 fortalezas concretas a potenciar, frases breves")
    observa: list[str] = Field(..., min_length=2, max_length=3, description="2-3 patrones a observar con consciencia, frases breves")
    evita: list[str] = Field(..., min_length=2, max_length=3, description="2-3 comportamientos o tendencias a evitar, frases breves")
    empieza: list[str] = Field(..., min_length=2, max_length=3, description="2-3 acciones concretas para empezar, frases breves")


class BrujulaPersonal(BaseModel):
    aprendizajes: list[str] = Field(..., min_length=5, max_length=5, description="Los 5 aprendizajes mas importantes que esta carta ofrece")
    mantra: str = Field(..., min_length=10, max_length=120, description="Una frase corta tipo mantra personal, memorable y accionable")
    frase_final: str = Field(..., min_length=40, max_length=250, description="Frase de cierre potente que sintetiza el espiritu de la carta, distinta a la frase_de_cierre del capitulo de sintesis")


class InterpretacionAreasDeVida(BaseModel):
    vocacion: str = Field(..., min_length=150, max_length=1800, description="Forma de trabajar, liderazgo, profesiones afines, donde puede destacar y que puede frenarle profesionalmente")
    dinero: str = Field(..., min_length=150, max_length=1800, description="Relacion con el dinero, como genera recursos, bloqueos, oportunidades y estrategias de crecimiento")
    amor: str = Field(..., min_length=150, max_length=1800, description="Como ama, que necesita, patrones relacionales, compatibilidad emocional y aprendizajes afectivos")
    herida_y_don: str = Field(..., min_length=150, max_length=1800, description="Interpretacion de Quiron enfocada en la herida, como aparece en la vida, como sanarla, y el don/regalo que hay detras de ella")
    aspectos_interpretados: list[AspectoInterpretado] = Field(..., description="Interpretacion de cada uno de los aspectos mas relevantes recibidos como input")
    plan_de_accion: PlanDeAccion
    brujula: BrujulaPersonal

class ProximosMeses(BaseModel):
    carrera: str = Field(..., min_length=80, max_length=700, description="Que viene en los proximos 3-6 meses en el area de carrera/vocacion")
    amor: str = Field(..., min_length=80, max_length=700, description="Que viene en los proximos 3-6 meses en el area de amor/relaciones")
    dinero: str = Field(..., min_length=80, max_length=700, description="Que viene en los proximos 3-6 meses en el area de dinero/recursos")
    crecimiento: str = Field(..., min_length=80, max_length=700, description="Que viene en los proximos 3-6 meses en el area de crecimiento personal/interior")
    
class InterpretacionTransitos(BaseModel):
    clima_energetico: str = Field(..., min_length=100, max_length=1100, description="Descripcion general del clima energetico actual segun los transitos activos")
    areas_activadas: list[str] = Field(..., min_length=2, max_length=4, description="2-4 areas de vida activadas ahora mismo, frases breves")
    oportunidades: str = Field(..., min_length=80, max_length=900, description="Oportunidades que ofrece el momento actual segun los transitos")
    retos: str = Field(..., min_length=80, max_length=900, description="Retos o tensiones del momento actual segun los transitos")
    consejo: str = Field(..., min_length=60, max_length=700, description="Consejo practico y accionable para navegar este momento")
    proximos_meses: ProximosMeses