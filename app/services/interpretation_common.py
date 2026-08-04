"""
Piezas compartidas por los 5 casos de uso de interpretacion via Claude
(interpretation_carta_completa.py, interpretation_resumen_gratuito.py,
interpretation_areas_de_vida.py, interpretation_transitos.py,
interpretation_horoscopos.py): cliente por defecto, parseo/validacion de
la respuesta cruda, y el bloque de instruccion de genero.
"""
import json
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError
from app.core.config import settings

# Cliente por defecto para los call sites existentes. Cada funcion publica
# de los modulos interpretation_*.py acepta `client` como parametro (con
# este singleton como default) para poder inyectar un cliente mockeado en
# tests sin llamar a la API real.
_client_default = AsyncAnthropic(api_key=settings.anthropic_api_key)


def _limpiar_json_markdown(texto: str) -> str:
    """
    Claude a veces envuelve el JSON en bloques markdown (```json ... ```)
    a pesar de que se le pida no hacerlo. Esta función lo quita si aparece.
    """
    texto = texto.strip()
    if texto.startswith("```"):
        # Quita la primera línea (```json o ```) y la última (```)
        lineas = texto.split("\n")
        if lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas and lineas[-1].strip() == "```":
            lineas = lineas[:-1]
        texto = "\n".join(lineas)
    return texto.strip()


def _parsear_respuesta(texto_crudo: str, schema: type[BaseModel]) -> dict:
    """
    Limpia bloques markdown si Claude los agrego, parsea el JSON y valida
    contra el schema Pydantic dado. Ante json.JSONDecodeError/ValidationError
    retorna un dict con _validation_error + _raw_response en vez de lanzar,
    para que los callers chequeen "_validation_error" en el dict en vez de
    depender de excepciones (ver CLAUDE.md, "Validacion en el borde").
    """
    texto_limpio = _limpiar_json_markdown(texto_crudo)
    try:
        datos_json = json.loads(texto_limpio)
        validado = schema(**datos_json)
        return validado.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        return {
            "_validation_error": str(e),
            "_raw_response": texto_crudo,
        }


def _instruccion_genero(genero: str | None, *, tercera_persona: bool = False) -> str:
    """
    Bloque de instruccion de genero inyectado en los prompts, para controlar
    la concordancia gramatical en espanol del texto que genera Claude.

    tercera_persona=True usa la variante breve de interpretar_transitos (ese
    prompt ya pide tercera persona fluida en sus reglas generales). El resto
    de los prompts usa la variante detallada, que ademas prohibe nombrar el
    genero como sustantivo ("esta mujer"/"este hombre") a favor de sujeto
    tacito o del pronombre correspondiente con moderacion.
    """
    if genero not in ("femenino", "masculino"):
        return "IMPORTANTE: no se especifico el genero de la persona. Usa lenguaje neutro donde sea posible.\n"

    if tercera_persona:
        if genero == "femenino":
            return "Genero de la persona: femenino. Ajusta la concordancia gramatical de adjetivos y participios a femenino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente.\n"
        return "Genero de la persona: masculino. Ajusta la concordancia gramatical de adjetivos y participios a masculino en toda la interpretacion. Escribe en tercera persona de forma fluida, dejando que la concordancia gramatical haga el trabajo silenciosamente.\n"

    if genero == "femenino":
        return "Genero de la persona: femenino. Ajusta la concordancia gramatical de adjetivos y participios a femenino en toda la interpretacion (ej. 'analitica', 'reservada'). PROHIBIDO usar las frases 'esta mujer' o 'esta persona es una mujer' como sujeto de una oracion — nunca nombres el genero como sustantivo. En su lugar, omite el sujeto (el espanol permite sujeto tacito: 'tiene', 'siente', 'busca' sin necesidad de decir 'ella' o 'esta mujer') o usa el pronombre 'ella' con moderacion, maximo 1-2 veces en todo el texto.\n"
    return "Genero de la persona: masculino. Ajusta la concordancia gramatical de adjetivos y participios a masculino en toda la interpretacion (ej. 'analitico', 'reservado'). PROHIBIDO usar las frases 'este hombre' o 'esta persona es un hombre' como sujeto de una oracion — nunca nombres el genero como sustantivo. En su lugar, omite el sujeto (el espanol permite sujeto tacito: 'tiene', 'siente', 'busca' sin necesidad de decir 'el' o 'este hombre') o usa el pronombre 'el' con moderacion, maximo 1-2 veces en todo el texto.\n"
