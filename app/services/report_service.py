from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
import os

from app.domain.rueda_natal_service import generar_rueda_svg, SIMBOLOS_PLANETAS

_RUTA_TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
_env = Environment(
    loader=FileSystemLoader(_RUTA_TEMPLATES),
    autoescape=True,
)


def _formatear_grados(valor: float) -> str:
    """24.617 -> "24°37'" (grados y minutos de arco, minutos truncados)."""
    grados = int(valor)
    minutos = int((valor - grados) * 60)
    return f"{grados}°{minutos:02d}'"


_env.filters["grados"] = _formatear_grados


def _parrafos(texto: str | None) -> list[str]:
    """Parte un texto de Claude en parrafos (por lineas en blanco o saltos)."""
    if not texto:
        return []
    return [p.strip() for p in texto.replace("\r", "").split("\n") if p.strip()]


_env.filters["parrafos"] = _parrafos

# Mapea el nombre del planeta (como aparece en el cálculo) a la clave usada
# en el JSON de interpretación (definida en interpretation_carta_completa.py)
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

def construir_contexto(metadata: dict, calculo: dict, interpretacion: dict) -> dict:
    """
    Arma el diccionario con planetas ya cruzados con su interpretación
    (join hecho en backend). Usado tanto para renderizar el PDF como
    para el endpoint JSON que consume el frontend.
    """
    planetas_con_interpretacion = {}
    for nombre, datos in calculo["planetas"].items():
        clave_interpretacion = MAPEO_INTERPRETACION.get(nombre)
        texto = interpretacion.get(clave_interpretacion, "") if clave_interpretacion else ""
        planetas_con_interpretacion[nombre] = {**datos, "interpretacion": texto}

    return dict(
        metadata=metadata,
        planetas=planetas_con_interpretacion,
        casas=calculo["casas"],
        puntos_angulares=calculo["puntos_angulares"],
        aspectos=calculo.get("aspectos", []),
        dignidades=calculo.get("dignidades", {}),
        elementos_y_modalidades=calculo.get("elementos_y_modalidades", {}),
        interpretacion=interpretacion,
    )


def generar_html_reporte(metadata: dict, calculo: dict, interpretacion: dict) -> str:
    template = _env.get_template("carta_report.html")
    contexto = construir_contexto(metadata, calculo, interpretacion)
    return template.render(**contexto)


def generar_html_calculo(metadata: dict, calculo: dict) -> str:
    """
    Renderiza solo el calculo astronomico/astrologico (sin interpretacion de
    Claude) como pagina HTML, para inspeccionar una carta sin pagar IA.
    """
    template = _env.get_template("carta_calculo.html")
    return template.render(
        metadata=metadata,
        planetas=calculo["planetas"],
        casas=calculo["casas"],
        puntos_angulares=calculo["puntos_angulares"],
        aspectos=calculo.get("aspectos", []),
        dignidades=calculo.get("dignidades", {}),
        elementos_y_modalidades=calculo.get("elementos_y_modalidades", {}),
    )


def _seccion_valida(datos: dict | None) -> dict | None:
    """None si la seccion no existe; se deja tal cual si trae _validation_error
    (el template la muestra como error para regenerarla desde el panel)."""
    return datos if datos else None


def generar_html_vista_previa(
    metadata: dict,
    calculo: dict,
    interpretacion: dict | None,
    areas_de_vida: dict | None,
    transitos: dict | None,
) -> str:
    """
    Vista previa HTML (solo admin) de todo lo que tiene una carta hasta el
    momento: rueda natal, calculo, interpretacion completa, areas de vida y
    transitos. Las secciones que aun no existen se muestran como pendientes.
    """
    template = _env.get_template("carta_vista_previa.html")
    contexto = construir_contexto(metadata, calculo, interpretacion or {})
    contexto.update(
        interpretacion=_seccion_valida(interpretacion),
        areas_de_vida=_seccion_valida(areas_de_vida),
        transitos=_seccion_valida(transitos),
        rueda_svg=Markup(generar_rueda_svg(calculo)),
        simbolos=SIMBOLOS_PLANETAS,
    )
    return template.render(**contexto)
