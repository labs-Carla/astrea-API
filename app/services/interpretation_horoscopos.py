from anthropic import AsyncAnthropic
from app.models.schemas import HoroscoposDelDia, HoroscoposDeLaSemana
from app.services.interpretation_common import _client_default, _parsear_respuesta, _log_uso_claude


SYSTEM_PROMPT_HOROSCOPOS = """Eres un astrologo profesional experimentado, con un enfoque psicologico moderno.
Vas a escribir horoscopos generales (no personalizados) para los 12 signos del zodiaco, basados en los
transitos planetarios actuales.

Reglas estrictas:
- Habla en terminos de arquetipo, tendencia y potencial — nunca en terminos deterministas o de prediccion literal.
- Cada horoscopo debe sentirse especifico al signo (usando su casa natural activada por cada transito), no
  intercambiable entre signos.
- Tono calido, claro y humano. Usa espanol latinoamericano neutro y cotidiano, evitando palabras rebuscadas.
- Nunca uses la frase "este hombre"/"esta mujer" ni te dirijas a un genero especifico — estos horoscopos son
  genericos para cualquier persona del signo.
- Responde UNICAMENTE con un objeto JSON valido, sin texto adicional antes o despues, ni bloques de markdown.
"""


def _construir_prompt_horoscopos(transitos_por_signo: dict, cadencia: str) -> str:
    """
    cadencia: 'diario' o 'semanal', ajusta la extension y el enfoque temporal
    del texto pedido.
    """
    extension = "100-150 palabras" if cadencia == "diario" else "150-220 palabras"
    marco_temporal = "de hoy" if cadencia == "diario" else "de esta semana"

    lineas = [f"Escribe el horoscopo {cadencia} ({marco_temporal}) para los 12 signos, basado en estos transitos:\n"]

    for signo, planetas in transitos_por_signo.items():
        lineas.append(f"\n--- {signo} ---")
        for nombre_planeta, datos in planetas.items():
            retro = " (retrogrado)" if datos["retrogrado"] else ""
            lineas.append(f"{nombre_planeta} en {datos['signo']}, activando su Casa {datos['casa_natural']}{retro}")

    lineas.append(f"""
Devuelve un JSON con exactamente esta forma:
{{
  "horoscopos": [
    {{"signo": "Aries", "texto": "horoscopo {marco_temporal} para Aries ({extension}), mencionando que areas de
      vida estan activadas segun las casas indicadas arriba"}},
    {{"signo": "Tauro", "texto": "..."}},
    ... (los 12 signos en orden zodiacal: Aries, Tauro, Geminis, Cancer, Leo, Virgo, Libra, Escorpio, Sagitario,
    Capricornio, Acuario, Piscis)
  ]
}}""")

    return "\n".join(lineas)


async def generar_horoscopos(
    transitos_por_signo: dict, cadencia: str, client: AsyncAnthropic = _client_default
) -> dict:
    """
    Genera los horoscopos genericos (diario o semanal) para los 12 signos,
    usando Haiku (contenido corto, no personalizado, no requiere el modelo
    mas costoso).
    """
    prompt_usuario = _construir_prompt_horoscopos(transitos_por_signo, cadencia)
    schema = HoroscoposDelDia if cadencia == "diario" else HoroscoposDeLaSemana

    respuesta = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        system=SYSTEM_PROMPT_HOROSCOPOS,
        messages=[{"role": "user", "content": prompt_usuario}],
    )

    _log_uso_claude(f"horoscopos_{cadencia}", respuesta)
    texto_crudo = respuesta.content[0].text.strip()
    return _parsear_respuesta(texto_crudo, schema)
