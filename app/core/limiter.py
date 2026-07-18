from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter compartido por toda la app. Se identifica al "cliente" por su IP
# (get_remote_address), para poder poner límites tipo "5 peticiones por
# minuto" sobre endpoints públicos sin autenticación, como el resumen gratis.
# Vive en su propio módulo (no en main.py) para evitar un import circular:
# endpoints.py necesita usar `limiter`, y main.py necesita el `router` de
# endpoints.py — si limiter viviera en main.py, se formaría un ciclo.
limiter = Limiter(key_func=get_remote_address)