"""
Prueba que el cliente de Claude inyectable (app/services/interpretation_common.py)
permite testear construccion de prompt + parseo de respuesta sin llamar a la API real,
para los 5 casos de uso repartidos en app/services/interpretation_*.py.
"""
import json
from types import SimpleNamespace

from app.services.interpretation_resumen_gratuito import interpretar_resumen_gratuito
from app.services.interpretation_carta_completa import interpretar_carta_completa
from app.services.interpretation_areas_de_vida import interpretar_areas_de_vida
from app.services.interpretation_transitos import interpretar_transitos
from app.services.interpretation_horoscopos import generar_horoscopos

SIGNOS_EN_ORDEN = [
    "Aries", "Tauro", "Geminis", "Cancer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]


class _FakeMessages:
    def __init__(self, texto_respuesta: str):
        self._texto_respuesta = texto_respuesta

    async def create(self, **kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text=self._texto_respuesta)])


class _FakeAnthropicClient:
    """Doble de AsyncAnthropic: mismo shape (`.messages.create`), sin red."""

    def __init__(self, texto_respuesta: str):
        self.messages = _FakeMessages(texto_respuesta)


def _calculo_minimo() -> dict:
    return {
        "planetas": {
            "Sol": {"signo": "Aries", "grado_en_signo": 10.0, "casa": 1, "retrogrado": False},
        },
        "puntos_angulares": {
            "Ascendente": {"signo": "Leo", "grado_en_signo": 5.0},
        },
        "aspectos": [],
    }


async def test_interpretar_resumen_gratuito_usa_el_cliente_inyectado():
    resumen_valido = "x" * 1600  # cumple min_length=1500 de InterpretacionResumen
    respuesta_json = json.dumps({"resumen": resumen_valido})
    cliente_falso = _FakeAnthropicClient(respuesta_json)

    resultado = await interpretar_resumen_gratuito(_calculo_minimo(), client=cliente_falso)

    assert "_validation_error" not in resultado
    assert resultado["resumen"] == resumen_valido


async def test_interpretar_resumen_gratuito_no_lanza_si_claude_responde_json_invalido():
    cliente_falso = _FakeAnthropicClient("esto no es json")

    resultado = await interpretar_resumen_gratuito(_calculo_minimo(), client=cliente_falso)

    assert "_validation_error" in resultado
    assert resultado["_raw_response"] == "esto no es json"


def _interpretacion_completa_valida() -> dict:
    return {
        "carta_en_una_mirada": {
            "esencia": "Analitica · Intensa · Curiosa",
            "talentos": ["Comprender a las personas", "Resolver problemas complejos", "Adaptarse rapido"],
            "desafios": ["Tendencia al perfeccionismo", "Exceso de analisis", "Dificultad para delegar"],
            "mision": "x" * 90,
        },
        "overview": "x" * 110,
        "lectura_elementos_dignidades": "x" * 90,
        "sol": "x" * 60,
        "luna": "x" * 60,
        "mercurio": "x" * 60,
        "venus": "x" * 60,
        "marte": "x" * 60,
        "jupiter": "x" * 60,
        "saturno": "x" * 60,
        "urano": "x" * 60,
        "neptuno": "x" * 60,
        "pluton": "x" * 60,
        "nodo_norte": "x" * 60,
        "quiron": "x" * 60,
        "ascendente": "x" * 60,
        "medio_cielo": "x" * 60,
        "conclusion": "x" * 90,
        "frase_de_cierre": "x" * 30,
    }


async def test_interpretar_carta_completa_usa_el_cliente_inyectado():
    esperado = _interpretacion_completa_valida()
    cliente_falso = _FakeAnthropicClient(json.dumps(esperado))

    resultado = await interpretar_carta_completa(_calculo_minimo(), client=cliente_falso)

    assert "_validation_error" not in resultado
    assert resultado["overview"] == esperado["overview"]


def _calculo_areas_de_vida() -> dict:
    """
    A diferencia de _calculo_minimo(), interpretar_areas_de_vida llama a
    calcular_regentes_de_casas() internamente (dominio real, no mockeado),
    asi que el calculo necesita las 12 casas y los 10 dispositores modernos
    presentes en `planetas` con su ubicacion completa.
    """
    casas = {str(i + 1): {"signo": signo} for i, signo in enumerate(SIGNOS_EN_ORDEN)}
    planetas_regentes = [
        "Marte", "Venus", "Mercurio", "Luna", "Sol",
        "Pluton", "Jupiter", "Saturno", "Urano", "Neptuno",
    ]
    planetas = {
        nombre: {"signo": "Geminis", "grado_en_signo": 12.5, "casa": 3, "retrogrado": False}
        for nombre in planetas_regentes
    }
    return {
        "casas": casas,
        "planetas": planetas,
        "puntos_angulares": {
            "Ascendente": {"signo": "Leo", "grado_en_signo": 5.0},
            "MedioCielo": {"signo": "Tauro", "grado_en_signo": 20.0},
        },
        "aspectos": [],
    }


def _interpretacion_areas_de_vida_valida() -> dict:
    return {
        "vocacion": "x" * 160,
        "dinero": "x" * 160,
        "amor": "x" * 160,
        "herida_y_don": "x" * 160,
        "aspectos_interpretados": [],
        "plan_de_accion": {
            "potencia": ["p1", "p2", "p3"],
            "observa": ["o1", "o2", "o3"],
            "evita": ["e1", "e2", "e3"],
            "empieza": ["em1", "em2", "em3"],
        },
        "brujula": {
            "aprendizajes": ["a1", "a2", "a3", "a4", "a5"],
            "mantra": "x" * 15,
            "frase_final": "x" * 45,
        },
    }


async def test_interpretar_areas_de_vida_usa_el_cliente_inyectado():
    esperado = _interpretacion_areas_de_vida_valida()
    cliente_falso = _FakeAnthropicClient(json.dumps(esperado))

    resultado = await interpretar_areas_de_vida(_calculo_areas_de_vida(), client=cliente_falso)

    assert "_validation_error" not in resultado
    assert resultado["vocacion"] == esperado["vocacion"]


def _calculo_natal_minimo() -> dict:
    return {
        "planetas": {
            "Sol": {"signo": "Aries", "casa": 1},
            "Luna": {"signo": "Cancer", "casa": 4},
        },
        "puntos_angulares": {
            "Ascendente": {"signo": "Leo"},
        },
    }


def _transitos_minimos() -> dict:
    return {
        "fecha_calculo": "2026-08-04",
        "planetas_transito": {
            "Jupiter": {"signo": "Geminis", "grado_en_signo": 15.0, "casa_natal": 3, "retrogrado": False},
        },
        "aspectos_transito": [
            {"planeta_transito": "Jupiter", "aspecto": "Trigono", "punto_natal": "Sol", "orbe_usado": 2.0},
        ],
    }


def _interpretacion_transitos_valida() -> dict:
    return {
        "clima_energetico": "x" * 110,
        "areas_activadas": ["Vocacion", "Vinculos cercanos"],
        "oportunidades": "x" * 90,
        "retos": "x" * 90,
        "consejo": "x" * 70,
        "proximos_meses": {
            "carrera": "x" * 90,
            "amor": "x" * 90,
            "dinero": "x" * 90,
            "crecimiento": "x" * 90,
        },
    }


async def test_interpretar_transitos_usa_el_cliente_inyectado():
    esperado = _interpretacion_transitos_valida()
    cliente_falso = _FakeAnthropicClient(json.dumps(esperado))

    resultado = await interpretar_transitos(_calculo_natal_minimo(), _transitos_minimos(), client=cliente_falso)

    assert "_validation_error" not in resultado
    assert resultado["clima_energetico"] == esperado["clima_energetico"]


def _transitos_por_signo_minimo() -> dict:
    return {
        "Aries": {
            "Marte": {"signo": "Aries", "casa_natural": 1, "retrogrado": False},
        },
    }


def _horoscopos_validos() -> dict:
    return {"horoscopos": [{"signo": signo, "texto": "x" * 90} for signo in SIGNOS_EN_ORDEN]}


async def test_generar_horoscopos_usa_el_cliente_inyectado():
    esperado = _horoscopos_validos()
    cliente_falso = _FakeAnthropicClient(json.dumps(esperado))

    resultado = await generar_horoscopos(_transitos_por_signo_minimo(), "diario", client=cliente_falso)

    assert "_validation_error" not in resultado
    assert len(resultado["horoscopos"]) == 12
