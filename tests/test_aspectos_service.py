from app.domain.aspectos_service import detectar_aspecto, calcular_todos_los_aspectos


def test_detectar_aspecto_conjuncion_exacta():
    resultado = detectar_aspecto(10.0, 10.0)
    assert resultado["aspecto"] == "Conjuncion"
    assert resultado["orbe_usado"] == 0.0


def test_detectar_aspecto_cuadratura_dentro_del_orbe():
    resultado = detectar_aspecto(0.0, 92.0)
    assert resultado["aspecto"] == "Cuadratura"
    assert resultado["orbe_usado"] == 2.0


def test_detectar_aspecto_ninguno_fuera_de_orbe():
    # 45 grados no cae dentro del orbe (8) de ningun aspecto mayor (0/60/90/120/180).
    assert detectar_aspecto(0.0, 45.0) is None


def test_detectar_aspecto_respeta_orbe_personalizado():
    # 65 grados esta a 5 de Sextil (60) -- entra con orbe 6, no con orbe 3.
    assert detectar_aspecto(0.0, 65.0, orbe=6) is not None
    assert detectar_aspecto(0.0, 65.0, orbe=3) is None


def test_calcular_todos_los_aspectos_excluye_ascendente_mediocielo():
    puntos = {
        "Sol": 0.0,
        "Luna": 0.0,  # conjuncion exacta con Sol
        "Ascendente": 10.0,
        "MedioCielo": 100.0,  # 90 grados de Ascendente -- cuadratura, pero excluida
    }

    aspectos = calcular_todos_los_aspectos(puntos)

    pares = [{a["punto_a"], a["punto_b"]} for a in aspectos]
    assert {"Ascendente", "MedioCielo"} not in pares
    assert {"Sol", "Luna"} in pares


def test_calcular_todos_los_aspectos_no_repite_ni_compara_consigo_mismo():
    puntos = {"Sol": 0.0, "Luna": 0.0}

    aspectos = calcular_todos_los_aspectos(puntos)

    assert len(aspectos) == 1
    assert aspectos[0]["punto_a"] == "Sol"
    assert aspectos[0]["punto_b"] == "Luna"
