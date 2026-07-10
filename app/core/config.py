from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AstroDev Agent API"
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()


# --- Constantes astrológicas ---

# Códigos de cuerpos celestes según pyswisseph (swe.SUN, swe.MOON, etc.)
# Se definen aquí como enteros para no depender de imports de swisseph fuera del cálculo.
PLANETAS = {
    "Sol": 0,        # swe.SUN
    "Luna": 1,       # swe.MOON
    "Mercurio": 2,   # swe.MERCURY
    "Venus": 3,      # swe.VENUS
    "Marte": 4,      # swe.MARS
    "Jupiter": 5,    # swe.JUPITER
    "Saturno": 6,    # swe.SATURN
    "Urano": 7,      # swe.URANUS
    "Neptuno": 8,    # swe.NEPTUNE
    "Pluton": 9,     # swe.PLUTO
    "NodoNorte": 10, # swe.MEAN_NODE
    "Quiron": 15,    # swe.CHIRON
}

SIGNOS = [
    "Aries", "Tauro", "Geminis", "Cancer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"
]

# Dispositores modernos: planeta regente de cada signo (escuela moderna, no tradicional)
DISPOSITORES_MODERNOS = {
    "Aries": "Marte",
    "Tauro": "Venus",
    "Geminis": "Mercurio",
    "Cancer": "Luna",
    "Leo": "Sol",
    "Virgo": "Mercurio",
    "Libra": "Venus",
    "Escorpio": "Pluton",
    "Sagitario": "Jupiter",
    "Capricornio": "Saturno",
    "Acuario": "Urano",
    "Piscis": "Neptuno",
}

# Aspectos mayores: nombre -> (ángulo exacto en grados, orbe permitido en grados)
ASPECTOS_MAYORES = {
    "Conjuncion": 0,
    "Sextil": 60,
    "Cuadratura": 90,
    "Trigono": 120,
    "Oposicion": 180,
}

ORBE_DEFAULT = 8  # grados de tolerancia alrededor del ángulo exacto

# --- Dignidades esenciales ---
# Cada planeta tiene: domicilio (uno o dos signos), exaltación (un signo),
# caída (el opuesto a la exaltación) y exilio (el opuesto al domicilio).

DOMICILIOS = {
    "Sol": ["Leo"],
    "Luna": ["Cancer"],
    "Mercurio": ["Geminis", "Virgo"],
    "Venus": ["Tauro", "Libra"],
    "Marte": ["Aries", "Escorpio"],
    "Jupiter": ["Sagitario", "Piscis"],
    "Saturno": ["Capricornio", "Acuario"],
    "Urano": ["Acuario"],
    "Neptuno": ["Piscis"],
    "Pluton": ["Escorpio"],
}

EXALTACIONES = {
    "Sol": "Aries",
    "Luna": "Tauro",
    "Mercurio": "Virgo",
    "Venus": "Piscis",
    "Marte": "Capricornio",
    "Jupiter": "Cancer",
    "Saturno": "Libra",
    "Urano": "Escorpio",
    "Neptuno": "Leo",
    "Pluton": "Acuario",
}

# Caída = signo opuesto a la exaltación
CAIDAS = {
    "Sol": "Libra",
    "Luna": "Escorpio",
    "Mercurio": "Piscis",
    "Venus": "Virgo",
    "Marte": "Cancer",
    "Jupiter": "Capricornio",
    "Saturno": "Aries",
    "Urano": "Tauro",
    "Neptuno": "Acuario",
    "Pluton": "Leo",
}

# Exilio = signo(s) opuesto(s) al domicilio
EXILIOS = {
    "Sol": ["Acuario"],
    "Luna": ["Capricornio"],
    "Mercurio": ["Sagitario", "Piscis"],
    "Venus": ["Aries", "Escorpio"],
    "Marte": ["Libra", "Tauro"],
    "Jupiter": ["Geminis", "Virgo"],
    "Saturno": ["Cancer", "Leo"],
    "Urano": ["Leo"],
    "Neptuno": ["Virgo"],
    "Pluton": ["Tauro"],
}


# --- Elementos y modalidades por signo ---

ELEMENTOS_POR_SIGNO = {
    "Aries": "Fuego", "Leo": "Fuego", "Sagitario": "Fuego",
    "Tauro": "Tierra", "Virgo": "Tierra", "Capricornio": "Tierra",
    "Geminis": "Aire", "Libra": "Aire", "Acuario": "Aire",
    "Cancer": "Agua", "Escorpio": "Agua", "Piscis": "Agua",
}

MODALIDADES_POR_SIGNO = {
    "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricornio": "Cardinal",
    "Tauro": "Fijo", "Leo": "Fijo", "Escorpio": "Fijo", "Acuario": "Fijo",
    "Geminis": "Mutable", "Virgo": "Mutable", "Sagitario": "Mutable", "Piscis": "Mutable",
}


