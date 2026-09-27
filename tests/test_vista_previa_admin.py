"""
GET /admin/carta/{id}/vista-previa: HTML solo-admin con rueda natal +
calculo + lo que exista de interpretacion/areas de vida/transitos. Las
secciones faltantes o con _validation_error se muestran como avisos.
"""
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.domain.rueda_natal_service import generar_rueda_svg, posiciones_de_dibujo
from app.main import app
from app.models.db_models import CartaNatalGuardada
from app.models.schemas import DatosNacimiento
from app.services.calculo_carta_service import calcular_todo

SECRETO = "secreto-de-test"
ADMIN = {"X-Admin-Secret": SECRETO}


def _calculo() -> dict:
    datos = DatosNacimiento(nombre="Ana", fecha_hora_local=datetime(1990, 5, 15, 14, 30), ciudad="Buenos Aires", pais="Argentina")
    # ida y vuelta por JSON: asi queda igual que al leerlo de la DB (claves de casas como str)
    return json.loads(json.dumps(calcular_todo(datos, -34.6, -58.38)["calculo"], default=str))


def _texto(marca: str, largo: int = 160) -> str:
    return (marca + " ") * (largo // (len(marca) + 1) + 1)


def _interpretacion() -> dict:
    planetas = ["sol", "luna", "mercurio", "venus", "marte", "jupiter", "saturno", "urano",
                "neptuno", "pluton", "nodo_norte", "quiron", "ascendente", "medio_cielo"]
    return {
        "carta_en_una_mirada": {"esencia": "ESENCIA-DE-PRUEBA", "talentos": ["t1", "t2", "t3"],
                                "desafios": ["d1", "d2", "d3"], "mision": "MISION-DE-PRUEBA"},
        "overview": _texto("OVERVIEW"),
        "lectura_elementos_dignidades": _texto("ELEMENTOS"),
        **{p: _texto(f"TEXTO-{p.upper()}") for p in planetas},
        "conclusion": _texto("CONCLUSION"),
        "frase_de_cierre": "FRASE-DE-CIERRE",
    }


def _areas() -> dict:
    return {
        "vocacion": _texto("VOCACION"), "dinero": _texto("DINERO"), "amor": _texto("AMOR"),
        "herida_y_don": _texto("HERIDA"),
        "aspectos_interpretados": [{"punto_a": "Sol", "aspecto": "Trigono", "punto_b": "Luna",
                                    "interpretacion": _texto("ASPECTO-SOL-LUNA")}],
        "plan_de_accion": {k: [f"{k}-1", f"{k}-2", f"{k}-3"] for k in ("potencia", "observa", "evita", "empieza")},
        "brujula": {"aprendizajes": ["a1", "a2", "a3", "a4", "a5"], "mantra": "MANTRA-DE-PRUEBA",
                    "frase_final": "FRASE-FINAL-BRUJULA"},
    }


def _transitos() -> dict:
    return {
        "clima_energetico": _texto("CLIMA"), "areas_activadas": ["area1", "area2"],
        "oportunidades": _texto("OPORTUNIDADES"), "retos": _texto("RETOS"), "consejo": _texto("CONSEJO"),
        "proximos_meses": {k: _texto(f"MESES-{k.upper()}", 90) for k in ("carrera", "amor", "dinero", "crecimiento")},
    }


@pytest.fixture
def app_client(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocalDeTest = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_db_override():
        db = SessionLocalDeTest()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(settings, "admin_secret", SECRETO)
    app.dependency_overrides[get_db] = _get_db_override
    try:
        yield TestClient(app), SessionLocalDeTest
    finally:
        app.dependency_overrides.pop(get_db, None)


def _crear_carta(SessionLocal, **jsons) -> int:
    with SessionLocal() as db:
        carta = CartaNatalGuardada(
            fecha_hora_local=datetime(1990, 5, 15, 14, 30), latitud=-34.6, longitud=-58.38,
            calculo_json=json.dumps(_calculo()), nombre_reporte="Ana Prueba", email="ana@example.com",
            **{k: json.dumps(v) for k, v in jsons.items()},
        )
        db.add(carta)
        db.commit()
        return carta.id


def test_vista_previa_completa_muestra_todas_las_secciones(app_client):
    client, SessionLocal = app_client
    carta_id = _crear_carta(SessionLocal, interpretacion_json=_interpretacion(),
                            areas_de_vida_json=_areas(), transitos_json=_transitos())

    respuesta = client.get(f"/api/v1/admin/carta/{carta_id}/vista-previa", headers=ADMIN)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    html = respuesta.text
    for marca in ("Ana Prueba", "<svg", "ESENCIA-DE-PRUEBA", "TEXTO-SOL", "TEXTO-MEDIO_CIELO", "ASPECTO-SOL-LUNA",
                  "VOCACION", "empieza-1", "MANTRA-DE-PRUEBA", "CLIMA", "MESES-CRECIMIENTO",
                  "FRASE-DE-CIERRE", "FRASE-FINAL-BRUJULA", "Casas (Placidus)"):
        assert marca in html, marca
    assert "Aún no se ha generado" not in html


def test_vista_previa_sin_interpretacion_muestra_calculo_y_pendientes(app_client):
    client, SessionLocal = app_client
    carta_id = _crear_carta(SessionLocal)

    html = client.get(f"/api/v1/admin/carta/{carta_id}/vista-previa", headers=ADMIN).text

    assert "<svg" in html and "Tauro 24°37&#39;" in html  # Sol calculado
    assert "Aún no se ha generado la interpretación completa" in html
    assert "Aún no se ha generado Áreas de vida" in html
    assert "Aún no se ha generado Tránsitos" in html


def test_vista_previa_con_error_de_validacion_lo_avisa(app_client):
    client, SessionLocal = app_client
    carta_id = _crear_carta(SessionLocal, interpretacion_json={"_validation_error": "json roto", "_raw_response": "x"})

    html = client.get(f"/api/v1/admin/carta/{carta_id}/vista-previa", headers=ADMIN).text

    assert "se generó con un error de formato" in html and "json roto" in html


def test_vista_previa_requiere_admin_y_404(app_client):
    client, SessionLocal = app_client
    carta_id = _crear_carta(SessionLocal)

    assert client.get(f"/api/v1/admin/carta/{carta_id}/vista-previa", headers={"X-Admin-Secret": "otra"}).status_code == 401
    assert client.get("/api/v1/admin/carta/999/vista-previa", headers=ADMIN).status_code == 404


def test_posiciones_de_dibujo_separa_planetas_juntos():
    dibujo = posiciones_de_dibujo({"Sol": 10.0, "Mercurio": 12.0, "Venus": 13.0, "Marte": 200.0})

    assert dibujo["Sol"] == 10.0 and dibujo["Marte"] == 200.0
    assert dibujo["Mercurio"] - dibujo["Sol"] >= 11 and dibujo["Venus"] - dibujo["Mercurio"] >= 11


def test_rueda_svg_tiene_signos_planetas_y_ejes():
    svg = generar_rueda_svg(_calculo())

    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert svg.count("♈") == 1 and "☉" in svg and ">AC<" in svg and ">MC<" in svg
