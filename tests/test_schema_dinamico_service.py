import pytest
from pydantic import BaseModel, ValidationError

from app.domain.schema_dinamico_service import construir_schema


def test_construir_schema_con_secciones_validas():
    secciones = [
        {"nombre": "vocacion", "min_chars": 150, "max_chars": 1800, "descripcion": "Vocación"},
        {"nombre": "dinero", "min_chars": 150, "max_chars": 1800, "descripcion": "Dinero"},
    ]

    schema = construir_schema(secciones)

    assert issubclass(schema, BaseModel)
    assert schema.__name__ == "InterpretacionDinamica"
    assert set(schema.model_fields.keys()) == {"vocacion", "dinero"}


def test_construir_schema_nombre_personalizado():
    secciones = [{"nombre": "clima", "min_chars": 80, "max_chars": 700, "descripcion": "Clima energético"}]

    schema = construir_schema(secciones, nombre_schema="InterpretacionClima")

    assert schema.__name__ == "InterpretacionClima"


def test_construir_schema_lista_vacia_lanza_value_error():
    with pytest.raises(ValueError):
        construir_schema([])


def test_construir_schema_min_mayor_que_max_lanza_value_error():
    secciones = [{"nombre": "vocacion", "min_chars": 1800, "max_chars": 150, "descripcion": "Vocación"}]

    with pytest.raises(ValueError):
        construir_schema(secciones)


def test_construir_schema_min_igual_a_max_lanza_value_error():
    secciones = [{"nombre": "vocacion", "min_chars": 500, "max_chars": 500, "descripcion": "Vocación"}]

    with pytest.raises(ValueError):
        construir_schema(secciones)


def test_schema_generado_rechaza_texto_mas_corto_que_min_chars():
    secciones = [{"nombre": "vocacion", "min_chars": 150, "max_chars": 1800, "descripcion": "Vocación"}]
    schema = construir_schema(secciones)

    with pytest.raises(ValidationError):
        schema(vocacion="demasiado corto")


def test_schema_generado_acepta_texto_dentro_del_rango():
    secciones = [{"nombre": "vocacion", "min_chars": 10, "max_chars": 100, "descripcion": "Vocación"}]
    schema = construir_schema(secciones)

    instancia = schema(vocacion="un texto que entra perfecto dentro del rango permitido")

    assert instancia.vocacion.startswith("un texto")


def test_schema_generado_rechaza_texto_mas_largo_que_max_chars():
    secciones = [{"nombre": "vocacion", "min_chars": 10, "max_chars": 20, "descripcion": "Vocación"}]
    schema = construir_schema(secciones)

    with pytest.raises(ValidationError):
        schema(vocacion="este texto tiene más de veinte caracteres de largo")
