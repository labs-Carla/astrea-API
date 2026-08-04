from app.services.astro_service import obtener_signo, calcular_casa_natural


def test_obtener_signo_inicio_de_signo():
    assert obtener_signo(0.0) == ("Aries", 0.0)


def test_obtener_signo_mitad_de_signo():
    signo, grado = obtener_signo(35.0)
    assert signo == "Tauro"
    assert grado == 5.0


def test_obtener_signo_normaliza_grados_mayores_a_360():
    signo, grado = obtener_signo(365.0)
    assert signo == "Aries"
    assert grado == 5.0


def test_calcular_casa_natural_mismo_signo_es_casa_1():
    assert calcular_casa_natural("Aries", "Aries") == 1


def test_calcular_casa_natural_ejemplo_del_docstring():
    # Venus en Cancer para una persona Aries activa su Casa 4 natural.
    assert calcular_casa_natural("Cancer", "Aries") == 4


def test_calcular_casa_natural_envuelve_el_zodiaco():
    # Piscis es el ultimo signo antes de volver a Aries -> Casa 12.
    assert calcular_casa_natural("Piscis", "Aries") == 12
