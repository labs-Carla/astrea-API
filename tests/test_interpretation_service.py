"""
Prueba que el cliente de Claude inyectable (app/services/interpretation_service.py)
permite testear construccion de prompt + parseo de respuesta sin llamar a la API real.
"""
import json
from types import SimpleNamespace

from app.services.interpretation_service import interpretar_resumen_gratuito


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
