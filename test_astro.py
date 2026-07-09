from datetime import datetime
from app.services.time_service import calcular_hora_utc, calcular_dia_juliano
from app.services.astro_service import calcular_casas, calcular_posiciones_planetarias
import swisseph as swe
import os
swe.set_ephe_path(os.path.join(os.getcwd(), "ephe"))

fecha_local = datetime(2000, 8, 25, 14, 50)
lat, lon = 4.5964, -74.0721

fecha_utc = calcular_hora_utc(fecha_local, lat, lon)
jd = calcular_dia_juliano(fecha_utc)

resultado_casas = calcular_casas(jd, lat, lon)
posiciones = calcular_posiciones_planetarias(jd, lat, resultado_casas["_armc"])

print("--- Puntos angulares ---")
print(resultado_casas["puntos_angulares"])

print("\n--- Planetas ---")
for planeta, datos in posiciones.items():
    print(planeta, datos)