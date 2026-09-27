"""
Flujo de compra sin webhook de Hotmart: la orden se crea ANTES del pago
(/carta-natal/orden, pago_confirmado=False), el admin la ve en
/admin/esperando-pago y la confirma a mano; recien ahi pasa a
/admin/pendientes y puede aprobarse. Geocodificacion mockeada.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import carta_natal
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.db_models import CartaNatalGuardada

SECRETO = "secreto-de-test"
ADMIN = {"X-Admin-Secret": SECRETO}
ORDEN = {
    "nombre": "Ana",
    "email": "ana@example.com",
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
    monkeypatch.setattr(settings, "admin_secret", SECRETO)
    app.dependency_overrides[get_db] = _get_db_override
    try:
        yield TestClient(app), SessionLocalDeTest
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_orden_nueva_queda_esperando_pago_y_no_en_pendientes(app_client):
    client, _ = app_client

    respuesta = client.post("/api/v1/carta-natal/orden", json=ORDEN)

    assert respuesta.status_code == 200
    orden_id = respuesta.json()["orden_id"]
    esperando = client.get("/api/v1/admin/esperando-pago", headers=ADMIN).json()
    assert [o["id"] for o in esperando] == [orden_id]
    assert esperando[0]["email"] == "ana@example.com"
    assert client.get("/api/v1/admin/pendientes", headers=ADMIN).json() == []


def test_confirmar_pago_mueve_la_orden_a_pendientes(app_client):
    client, _ = app_client
    orden_id = client.post("/api/v1/carta-natal/orden", json=ORDEN).json()["orden_id"]

    respuesta = client.post(f"/api/v1/admin/confirmar-pago/{orden_id}", headers=ADMIN)

    assert respuesta.json()["status"] == "confirmado"
    assert client.get("/api/v1/admin/esperando-pago", headers=ADMIN).json() == []
    assert [c["id"] for c in client.get("/api/v1/admin/pendientes", headers=ADMIN).json()] == [orden_id]
    repetida = client.post(f"/api/v1/admin/confirmar-pago/{orden_id}", headers=ADMIN)
    assert repetida.json()["status"] == "ya_confirmado"


def test_aprobar_orden_sin_pago_confirmado_devuelve_409(app_client):
    client, SessionLocalDeTest = app_client
    orden_id = client.post("/api/v1/carta-natal/orden", json=ORDEN).json()["orden_id"]
    with SessionLocalDeTest() as db:
        carta = db.get(CartaNatalGuardada, orden_id)
        carta.interpretacion_json = "{}"
        db.commit()

    respuesta = client.post(f"/api/v1/admin/aprobar/{orden_id}", headers=ADMIN)

    assert respuesta.status_code == 409


def test_compra_legada_post_pago_queda_confirmada(app_client):
    client, _ = app_client

    client.post("/api/v1/carta-natal/compra", json=ORDEN)

    assert client.get("/api/v1/admin/esperando-pago", headers=ADMIN).json() == []
    assert len(client.get("/api/v1/admin/pendientes", headers=ADMIN).json()) == 1


def test_orden_repetida_no_des_confirma_un_pago_ya_confirmado(app_client):
    client, _ = app_client
    client.post("/api/v1/carta-natal/compra", json=ORDEN)

    client.post("/api/v1/carta-natal/orden", json=ORDEN)

    assert client.get("/api/v1/admin/esperando-pago", headers=ADMIN).json() == []


def test_endpoints_de_pago_requieren_admin(app_client):
    client, _ = app_client

    incorrecta = {"X-Admin-Secret": "otra-clave"}

    assert client.get("/api/v1/admin/esperando-pago", headers=incorrecta).status_code == 401
    assert client.post("/api/v1/admin/confirmar-pago/1", headers=incorrecta).status_code == 401
