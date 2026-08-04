from app.services.dignidades_service import calcular_dignidad


def test_calcular_dignidad_domicilio():
    assert calcular_dignidad("Sol", "Leo") == "Domicilio"


def test_calcular_dignidad_exaltacion():
    assert calcular_dignidad("Sol", "Aries") == "Exaltacion"


def test_calcular_dignidad_caida():
    assert calcular_dignidad("Sol", "Libra") == "Caida"


def test_calcular_dignidad_exilio():
    assert calcular_dignidad("Sol", "Acuario") == "Exilio"


def test_calcular_dignidad_ninguna():
    assert calcular_dignidad("Sol", "Tauro") is None


def test_calcular_dignidad_domicilio_con_dos_signos_posibles():
    # Venus rige tanto Tauro como Libra.
    assert calcular_dignidad("Venus", "Tauro") == "Domicilio"
    assert calcular_dignidad("Venus", "Libra") == "Domicilio"
