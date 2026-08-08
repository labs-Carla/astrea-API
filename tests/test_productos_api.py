"""
Primer test de integracion HTTP del repo (TestClient) -- no habia ninguno
todavia, ver TECH_DEBT.md #3 ("no hay tests de integracion de endpoints").
Cubre solo GET /productos/token/{token} (el endpoint publico agregado en
este cambio), no expande el alcance a los otros endpoints de productos.py
que ya existian sin tests de integracion.
"""
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.db_models import CartaNatalGuardada, ProductoConfig, ProductoGenerado


@pytest.fixture
def app_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocalDeTest = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_db_override():
        db = SessionLocalDeTest()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_override
    try:
        yield TestClient(app), SessionLocalDeTest
    finally:
        app.dependency_overrides.pop(get_db, None)


def _crear_carta(db) -> CartaNatalGuardada:
    carta = CartaNatalGuardada(
        fecha_hora_local=datetime(2000, 1, 1, 12, 0, 0),
        latitud=-34.6,
        longitud=-58.4,
        calculo_json=json.dumps({"planetas": {}}),
    )
    db.add(carta)
    db.commit()
    db.refresh(carta)
    return carta


def _crear_config(db) -> ProductoConfig:
    config = ProductoConfig(
        codigo="reporte_test",
        nombre="Reporte Test",
        system_prompt="x",
        instrucciones_usuario_template="x",
        secciones_json="[]",
        inputs_requeridos_json="[]",
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _crear_producto_generado(
    db, config: ProductoConfig, carta: CartaNatalGuardada, estado: str, token: str | None, contenido: dict | None = None
) -> ProductoGenerado:
    producto = ProductoGenerado(
        carta_id=carta.id,
        producto_codigo=config.codigo,
        inputs_json="{}",
        contenido_json=json.dumps(contenido) if contenido is not None else None,
        estado=estado,
        token=token,
        fecha_generacion=datetime(2026, 1, 1, 12, 0, 0),
    )
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def test_token_invalido_devuelve_404(app_client):
    client, _ = app_client

    respuesta = client.get("/api/v1/productos/token/token-que-no-existe")

    assert respuesta.status_code == 404


def test_producto_pendiente_devuelve_409_sin_exponer_contenido(app_client):
    client, SessionLocalDeTest = app_client
    db = SessionLocalDeTest()
    carta = _crear_carta(db)
    config = _crear_config(db)
    _crear_producto_generado(db, config, carta, estado="pendiente", token="tok-pendiente")
    db.close()

    respuesta = client.get("/api/v1/productos/token/tok-pendiente")

    assert respuesta.status_code == 409
    assert "contenido" not in respuesta.json()


def test_producto_generado_sin_aprobar_devuelve_409(app_client):
    client, SessionLocalDeTest = app_client
    db = SessionLocalDeTest()
    carta = _crear_carta(db)
    config = _crear_config(db)
    _crear_producto_generado(
        db, config, carta, estado="generado", token="tok-generado",
        contenido={"seccion_uno": "todavia no deberia verse"},
    )
    db.close()

    respuesta = client.get("/api/v1/productos/token/tok-generado")

    assert respuesta.status_code == 409
    assert "contenido" not in respuesta.json()


def test_producto_aprobado_devuelve_200_con_contenido(app_client):
    client, SessionLocalDeTest = app_client
    db = SessionLocalDeTest()
    carta = _crear_carta(db)
    config = _crear_config(db)
    _crear_producto_generado(
        db, config, carta, estado="aprobado", token="tok-aprobado",
        contenido={"seccion_uno": "contenido final aprobado"},
    )
    db.close()

    respuesta = client.get("/api/v1/productos/token/tok-aprobado")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "aprobado"
    assert cuerpo["nombre_producto"] == "Reporte Test"
    assert cuerpo["contenido"] == {"seccion_uno": "contenido final aprobado"}


def test_producto_enviado_devuelve_200_con_contenido(app_client):
    client, SessionLocalDeTest = app_client
    db = SessionLocalDeTest()
    carta = _crear_carta(db)
    config = _crear_config(db)
    _crear_producto_generado(
        db, config, carta, estado="enviado", token="tok-enviado",
        contenido={"seccion_uno": "contenido ya enviado al cliente"},
    )
    db.close()

    respuesta = client.get("/api/v1/productos/token/tok-enviado")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "enviado"
    assert cuerpo["contenido"] == {"seccion_uno": "contenido ya enviado al cliente"}
