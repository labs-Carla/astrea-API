"""
Prueba generacion_producto_service con un cliente de Claude mockeado, mismo
patron que test_interpretation_service.py -- sin llamar a la API real, y con
una DB sqlite en memoria para poder ejercitar el flujo completo (config +
carta -> ProductoGenerado persistido).
"""
import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.db_models import CartaNatalGuardada, ProductoConfig
from app.services.generacion_producto_service import generar_producto
from app.infrastructure.persistence_service import crear_producto_config, guardar_carta_completa


class _FakeMessages:
    def __init__(self, texto_respuesta: str):
        self._texto_respuesta = texto_respuesta
        self.llamadas = 0

    async def create(self, **kwargs):
        self.llamadas += 1
        return SimpleNamespace(
            content=[SimpleNamespace(text=self._texto_respuesta)],
            model=kwargs["model"],
            usage=SimpleNamespace(input_tokens=100, output_tokens=200),
        )


class _FakeAnthropicClient:
    """Doble de AsyncAnthropic: mismo shape (`.messages.create`), sin red."""

    def __init__(self, texto_respuesta: str):
        self.messages = _FakeMessages(texto_respuesta)


SECCIONES_TEST = [
    {"nombre": "seccion_uno", "min_chars": 5, "max_chars": 200, "descripcion": "Seccion de prueba"},
]


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _calculo_minimo() -> dict:
    return {
        "planetas": {
            "Sol": {"signo": "Aries", "grado_en_signo": 10.0, "casa": 1, "retrogrado": False},
        },
        "casas": {1: {"signo": "Aries"}},
        "dignidades": {},
        "aspectos": [],
        "elementos_y_modalidades": {},
    }


def _crear_carta(db) -> CartaNatalGuardada:
    return guardar_carta_completa(
        db,
        fecha_hora_local=datetime(2000, 1, 1, 12, 0, 0),
        latitud=-34.6,
        longitud=-58.4,
        calculo=_calculo_minimo(),
        interpretacion=None,
    )


def _crear_config(
    db,
    codigo: str = "reporte_test",
    criterios_json: str | None = None,
    temas_a_criterios_json: str | None = None,
    inputs_requeridos: list[str] | None = None,
) -> ProductoConfig:
    return crear_producto_config(
        db,
        codigo=codigo,
        nombre="Reporte Test",
        system_prompt="Sos un asistente de test.",
        instrucciones_usuario_template="Nombre: {nombre}. Foco: {foco_json}",
        criterios_json=criterios_json,
        temas_a_criterios_json=temas_a_criterios_json,
        secciones_json=json.dumps(SECCIONES_TEST),
        inputs_requeridos_json=json.dumps(inputs_requeridos if inputs_requeridos is not None else ["nombre"]),
    )


async def test_generar_producto_con_criterios_fijo_genera_correctamente(db):
    carta = _crear_carta(db)
    config = _crear_config(db, criterios_json=json.dumps({"puntos": ["Sol"]}))
    respuesta_json = json.dumps({"seccion_uno": "un texto de prueba con longitud suficiente"})
    cliente_falso = _FakeAnthropicClient(respuesta_json)

    resultado = await generar_producto(db, carta.id, config.codigo, {"nombre": "Juan"}, client=cliente_falso)

    assert resultado.estado == "generado"
    assert cliente_falso.messages.llamadas == 1
    contenido = json.loads(resultado.contenido_json)
    assert contenido["seccion_uno"] == "un texto de prueba con longitud suficiente"


async def test_generar_producto_con_tema_resuelve_el_tema_correcto(db):
    carta = _crear_carta(db)
    temas = {"amor": {"puntos": ["Sol"]}, "dinero": {"puntos": ["Sol"]}}
    config = _crear_config(db, temas_a_criterios_json=json.dumps(temas))
    respuesta_json = json.dumps({"seccion_uno": "un texto de prueba con longitud suficiente"})
    cliente_falso = _FakeAnthropicClient(respuesta_json)

    resultado = await generar_producto(
        db, carta.id, config.codigo, {"nombre": "Juan", "tema": "amor"}, client=cliente_falso
    )

    assert resultado.estado == "generado"
    assert cliente_falso.messages.llamadas == 1


async def test_tema_inexistente_lanza_value_error_sin_llamar_a_claude(db):
    carta = _crear_carta(db)
    temas = {"amor": {"puntos": ["Sol"]}}
    config = _crear_config(db, temas_a_criterios_json=json.dumps(temas))
    cliente_falso = _FakeAnthropicClient(json.dumps({"seccion_uno": "no deberia usarse"}))

    with pytest.raises(ValueError):
        await generar_producto(
            db, carta.id, config.codigo, {"nombre": "Juan", "tema": "inexistente"}, client=cliente_falso
        )

    assert cliente_falso.messages.llamadas == 0


async def test_input_requerido_faltante_lanza_value_error_antes_de_llamar_a_claude(db):
    carta = _crear_carta(db)
    config = _crear_config(db, criterios_json=json.dumps({"puntos": ["Sol"]}), inputs_requeridos=["nombre"])
    cliente_falso = _FakeAnthropicClient(json.dumps({"seccion_uno": "no deberia usarse"}))

    with pytest.raises(ValueError):
        await generar_producto(db, carta.id, config.codigo, {}, client=cliente_falso)

    assert cliente_falso.messages.llamadas == 0


async def test_respuesta_invalida_de_claude_guarda_estado_fallido(db):
    carta = _crear_carta(db)
    config = _crear_config(db, criterios_json=json.dumps({"puntos": ["Sol"]}))
    cliente_falso = _FakeAnthropicClient("esto no es json")

    resultado = await generar_producto(db, carta.id, config.codigo, {"nombre": "Juan"}, client=cliente_falso)

    assert resultado.estado == "fallido"
    contenido = json.loads(resultado.contenido_json)
    assert "_validation_error" in contenido
