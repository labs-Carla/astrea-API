"""
Rueda natal en SVG (puro, sin dependencias externas). Port a Python del
tema claro de rueda-natal.js de la landing (astrea-landing), para poder
renderizar la rueda desde el servidor en la vista previa HTML del admin.

Convencion: el Ascendente queda fijo a la izquierda (9 en punto) y los
grados avanzan en sentido antihorario, como en cualquier carta natal.
"""
import math

from app.domain.astro_constants import SIGNOS, ELEMENTOS_POR_SIGNO

# ︎ fuerza presentacion de texto (no emoji a color) en los glifos,
# igual que en la landing.
SIMBOLOS_SIGNOS = [s + "︎" for s in "♈♉♊♋♌♍♎♏♐♑♒♓"]

SIMBOLOS_PLANETAS = {
    "Sol": "☉", "Luna": "☽", "Mercurio": "☿", "Venus": "♀", "Marte": "♂",
    "Jupiter": "♃", "Saturno": "♄", "Urano": "♅", "Neptuno": "♆", "Pluton": "♇",
    "NodoNorte": "☊", "Quiron": "⚷",
}
SIMBOLOS_PLANETAS = {k: v + "︎" for k, v in SIMBOLOS_PLANETAS.items()}

ESTILOS_ASPECTO = {
    "Conjuncion": ("#8C5F24", None),
    "Trigono": ("#5B8A66", None),
    "Sextil": ("#5B8A66", "3,3"),
    "Cuadratura": ("#B0503F", None),
    "Oposicion": ("#B0503F", "3,3"),
}

COLOR_ELEMENTO = {
    "Fuego": "rgba(196,106,84,0.16)",
    "Tierra": "rgba(140,130,70,0.16)",
    "Aire": "rgba(122,92,166,0.14)",
    "Agua": "rgba(90,140,158,0.14)",
}

ORO = "#B8914A"
LINEA = "rgba(120,100,60,0.35)"
TINTA = "#2A2520"
CREMA = "#FFFCF6"

CX = CY = 200
# Anillos, de afuera hacia adentro: signos (150-185), numeros de casa (~139),
# planetas (116) y el circulo interior de aspectos (92), como en una carta
# estandar: las lineas de aspectos no cruzan los numeros ni los glifos.
R_EXTERIOR, R_SIGNOS, R_NUMEROS, R_PLANETAS, R_ASPECTOS = 185, 150, 139, 116, 92
SEPARACION_MINIMA = 11.0  # grados entre glifos (~22px a R_PLANETAS, el diametro de un glifo)


def _angulo(grado: float, asc: float) -> float:
    """Grado absoluto -> radianes en el SVG, con el Ascendente a 180°."""
    relativo = (asc - grado + 360) % 360
    return math.radians(180 - relativo)


def _punto(radio: float, rad: float) -> tuple[float, float]:
    return CX + radio * math.cos(rad), CY - radio * math.sin(rad)


def _cuna(r_int: float, r_ext: float, g_ini: float, g_fin: float, asc: float, pasos: int = 8) -> str:
    externos = [_punto(r_ext, _angulo(g_ini + (g_fin - g_ini) * k / pasos, asc)) for k in range(pasos + 1)]
    internos = [_punto(r_int, _angulo(g_ini + (g_fin - g_ini) * k / pasos, asc)) for k in range(pasos, -1, -1)]
    return "M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in externos + internos) + "Z"


def posiciones_de_dibujo(longitudes: dict[str, float]) -> dict[str, float]:
    """
    Separa planetas muy juntos (ej. conjunciones) para que sus glifos no se
    pisen: recorre en orden de longitud y empuja cada uno al menos
    SEPARACION_MINIMA grados del anterior. Solo afecta donde se DIBUJA el
    glifo; la posicion real se marca aparte con una muesca.
    """
    ordenados = sorted(longitudes.items(), key=lambda par: par[1])
    dibujo: dict[str, float] = {}
    anterior = None
    for nombre, grado in ordenados:
        if anterior is not None and grado - anterior < SEPARACION_MINIMA:
            grado = anterior + SEPARACION_MINIMA
        dibujo[nombre] = grado
        anterior = grado
    return dibujo


def _longitud(nombre: str, calculo: dict) -> float | None:
    if nombre in calculo["planetas"]:
        return calculo["planetas"][nombre]["longitud_absoluta"]
    if nombre in calculo["puntos_angulares"]:
        return calculo["puntos_angulares"][nombre]["longitud_absoluta"]
    return None


def generar_rueda_svg(calculo: dict) -> str:
    """Devuelve el <svg> completo de la rueda natal para un calculo de carta."""
    asc = calculo["puntos_angulares"]["Ascendente"]["longitud_absoluta"]
    mc = calculo["puntos_angulares"]["MedioCielo"]["longitud_absoluta"]
    partes = [
        '<svg viewBox="-20 -20 440 440" xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-label="Rueda natal" font-family="\'DM Sans\', system-ui, sans-serif">',
        f'<circle cx="{CX}" cy="{CY}" r="{R_EXTERIOR}" fill="{CREMA}"/>',
    ]

    # Anillo de signos con lavado elemental
    for i, signo in enumerate(SIGNOS):
        g = i * 30
        partes.append(f'<path d="{_cuna(R_SIGNOS, R_EXTERIOR, g, g + 30, asc)}" fill="{COLOR_ELEMENTO[ELEMENTOS_POR_SIGNO[signo]]}"/>')
        x1, y1 = _punto(R_SIGNOS, _angulo(g, asc))
        x2, y2 = _punto(R_EXTERIOR, _angulo(g, asc))
        partes.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{LINEA}"/>')
        x, y = _punto((R_EXTERIOR + R_SIGNOS) / 2, _angulo(g + 15, asc))
        partes.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="17" fill="{TINTA}" text-anchor="middle" '
            f'dominant-baseline="central">{SIMBOLOS_SIGNOS[i]}</text>'
        )

    partes.append(f'<circle cx="{CX}" cy="{CY}" r="{R_EXTERIOR}" fill="none" stroke="{LINEA}"/>')
    partes.append(f'<circle cx="{CX}" cy="{CY}" r="{R_SIGNOS}" fill="none" stroke="{LINEA}"/>')
    partes.append(f'<circle cx="{CX}" cy="{CY}" r="{R_ASPECTOS}" fill="none" stroke="{LINEA}" stroke-width="0.8"/>')

    # Cuspides reales de casas; Casa 1 (AC) y 10 (MC) resaltadas
    cuspides = [calculo["casas"][str(n)]["longitud_absoluta"] if str(n) in calculo["casas"]
                else calculo["casas"][n]["longitud_absoluta"] for n in range(1, 13)]
    for idx, grado in enumerate(cuspides):
        es_eje = idx in (0, 9)
        x_i, y_i = _punto(R_ASPECTOS, _angulo(grado, asc))
        x_e, y_e = _punto(R_SIGNOS, _angulo(grado, asc))
        partes.append(
            f'<line x1="{x_i:.2f}" y1="{y_i:.2f}" x2="{x_e:.2f}" y2="{y_e:.2f}" '
            f'stroke="{ORO if es_eje else LINEA}" stroke-width="{1.6 if es_eje else 0.75}"/>'
        )
        siguiente = cuspides[(idx + 1) % 12]
        medio = grado + ((siguiente - grado) % 360) / 2
        x, y = _punto(R_NUMEROS, _angulo(medio, asc))
        partes.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="9.5" fill="#8B7A5C" text-anchor="middle" '
            f'dominant-baseline="central">{idx + 1}</text>'
        )

    for etiqueta, grado in (("AC", asc), ("MC", mc)):
        x, y = _punto(R_EXTERIOR + 13, _angulo(grado, asc))
        partes.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="10" font-weight="600" fill="{ORO}" '
            f'text-anchor="middle" dominant-baseline="central">{etiqueta}</text>'
        )

    # Aspectos (entre posiciones reales, no las desplazadas)
    for asp in calculo.get("aspectos", []):
        g_a, g_b = _longitud(asp["punto_a"], calculo), _longitud(asp["punto_b"], calculo)
        if g_a is None or g_b is None:
            continue
        color, dash = ESTILOS_ASPECTO.get(asp["aspecto"], ("#5A5249", None))
        xa, ya = _punto(R_ASPECTOS, _angulo(g_a, asc))
        xb, yb = _punto(R_ASPECTOS, _angulo(g_b, asc))
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        partes.append(
            f'<line x1="{xa:.2f}" y1="{ya:.2f}" x2="{xb:.2f}" y2="{yb:.2f}" stroke="{color}" '
            f'stroke-width="1" opacity="0.6"{dash_attr}/>'
        )

    # Planetas: muesca en el grado real + glifo en la posicion de dibujo
    reales = {n: p["longitud_absoluta"] for n, p in calculo["planetas"].items()}
    dibujo = posiciones_de_dibujo(reales)
    for nombre, real in reales.items():
        x1, y1 = _punto(R_SIGNOS, _angulo(real, asc))
        x2, y2 = _punto(R_SIGNOS - 5, _angulo(real, asc))
        partes.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{TINTA}" stroke-width="1.2"/>')
        xg, yg = _punto(R_PLANETAS, _angulo(dibujo[nombre], asc))
        if abs(dibujo[nombre] - real) > 0.01:
            partes.append(
                f'<line x1="{x2:.2f}" y1="{y2:.2f}" x2="{xg:.2f}" y2="{yg:.2f}" stroke="{LINEA}" stroke-width="0.6"/>'
            )
        destacado = nombre in ("Sol", "Luna")
        relleno, texto = (ORO, CREMA) if destacado else (CREMA, TINTA)
        partes.append(f'<circle cx="{xg:.2f}" cy="{yg:.2f}" r="11.5" fill="{relleno}" stroke="{ORO if destacado else LINEA}"/>')
        retro = calculo["planetas"][nombre].get("retrogrado")
        partes.append(
            f'<text x="{xg:.2f}" y="{yg:.2f}" font-size="13" fill="{texto}" text-anchor="middle" '
            f'dominant-baseline="central">{SIMBOLOS_PLANETAS.get(nombre, nombre[0])}</text>'
        )
        if retro:
            partes.append(
                f'<text x="{xg + 10:.2f}" y="{yg + 9:.2f}" font-size="7" fill="#B0503F" '
                f'text-anchor="middle" dominant-baseline="central">R</text>'
            )

    partes.append("</svg>")
    return "".join(partes)
