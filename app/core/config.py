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


