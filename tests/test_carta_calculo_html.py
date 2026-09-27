"""
Test de integracion HTTP de GET /carta-natal/calculo: pagina HTML con el
calculo completo (sin IA). Se mockea la geocodificacion para no depender
de Nominatim; el calculo con Swiss Ephemeris es real.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import carta_natal
from app.core.database import Base, get_db
from app.main import app
from app.models.db_models import CartaNatalGuardada
from app.services.report_service import _formatear_grados

URL = "/api/v1/carta-natal/calculo"
PARAMS = {
    "nombre": "Ana",
    "fecha_hora_local": "1990-05-15T14:30:00",
    "ciudad": "Buenos Aires",
    "pais": "Argentina",
}


@pytest.fixture
def app_client(monkeypatch):
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

    monkeypatch.setattr(carta_natal, "geocodificar_ciudad", lambda ciudad, pais: (-34.6, -58.38))
    app.dependency_overrides[get_db] = _get_db_override
    try:
        yield TestClient(app), SessionLocalDeTest
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_calculo_html_renderiza_carta_completa_sin_persistir(app_client):
    client, SessionLocalDeTest = app_client

    respuesta = client.get(URL, params=PARAMS)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    html = respuesta.text
    for fragmento in ("Ana", "Puntos angulares", "Ascendente", "Planetas", "Quiron", "Casa 12", "Aspectos", "Elementos"):
        assert fragmento in html
    # Sol en Tauro 24°37' para estos datos (valor calculado con Swiss Ephemeris)
    assert "24°37&#39;" in html

    with SessionLocalDeTest() as db:
        assert db.query(CartaNatalGuardada).count() == 0


def test_calculo_html_ciudad_invalida_devuelve_400(app_client, monkeypatch):
    client, _ = app_client

    def _falla(ciudad, pais):
        raise ValueError("No se encontro la ciudad")

    monkeypatch.setattr(carta_natal, "geocodificar_ciudad", _falla)

    respuesta = client.get(URL, params=PARAMS)

    assert respuesta.status_code == 400


def test_calculo_html_faltan_params_devuelve_422(app_client):
    client, _ = app_client

    respuesta = client.get(URL, params={"nombre": "Ana"})

    assert respuesta.status_code == 422


def test_formatear_grados():
    assert _formatear_grados(24.617064966) == "24°37'"
    assert _formatear_grados(0.0) == "0°00'"
    assert _formatear_grados(29.9994) == "29°59'"
