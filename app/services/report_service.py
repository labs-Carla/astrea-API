from jinja2 import Environment, FileSystemLoader
import os

_RUTA_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
_env = Environment(loader=FileSystemLoader(_RUTA_TEMPLATES))


def generar_html_reporte(metadata: dict, calculo: dict) -> str:
    """
    Renderiza la plantilla carta_report.html con los datos calculados.
    """
    template = _env.get_template("carta_report.html")

    html = template.render(
        metadata=metadata,
        planetas=calculo["planetas"],
        casas=calculo["casas"],
        puntos_angulares=calculo["puntos_angulares"],
    )

    return html