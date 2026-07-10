from jinja2 import Environment, FileSystemLoader
import os

_RUTA_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
_env = Environment(loader=FileSystemLoader(_RUTA_TEMPLATES))

# Mapea el nombre del planeta (como aparece en el cálculo) a la clave usada
# en el JSON de interpretación (definida en interpretation_service.py)
MAPEO_INTERPRETACION = {
    "Sol": "sol",
    "Luna": "luna",
    "Mercurio": "mercurio",
    "Venus": "venus",
    "Marte": "marte",
    "Jupiter": "jupiter",
    "Saturno": "saturno",
    "Urano": "urano",
    "Neptuno": "neptuno",
    "Pluton": "pluton",
    "NodoNorte": "nodo_norte",
    "Quiron": "quiron",
}


def generar_html_reporte(metadata: dict, calculo: dict, interpretacion: dict) -> str:
    """
    Renderiza la plantilla carta_report.html con los datos calculados y
    la interpretación generada por IA.
    """
    template = _env.get_template("carta_report.html")

    # Adjunta el texto interpretativo a cada planeta, usando el mapeo de claves
    planetas_con_interpretacion = {}
    for nombre, datos in calculo["planetas"].items():
        clave_interpretacion = MAPEO_INTERPRETACION.get(nombre)
        texto = interpretacion.get(clave_interpretacion, "") if clave_interpretacion else ""
        planetas_con_interpretacion[nombre] = {**datos, "interpretacion": texto}

    html = template.render(
    metadata=metadata,
    planetas=planetas_con_interpretacion,
    casas=calculo["casas"],
    puntos_angulares=calculo["puntos_angulares"],
    aspectos=calculo.get("aspectos", []),
    dignidades=calculo.get("dignidades", {}),
    elementos_y_modalidades=calculo.get("elementos_y_modalidades", {}),
    interpretacion=interpretacion,
)

    return html