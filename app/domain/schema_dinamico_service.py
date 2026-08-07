from pydantic import BaseModel, Field, create_model


def construir_schema(secciones: list[dict], nombre_schema: str = "InterpretacionDinamica") -> type[BaseModel]:
    """
    Convierte una definición de secciones (la forma en que va a vivir un
    producto en la futura tabla `producto_configs`) en una clase Pydantic
    real, generada en tiempo de ejecución con `create_model`.

    Esto existe para poder dar de alta un producto/reporte nuevo (un set
    de secciones) sin escribir a mano una clase Pydantic por cada uno en
    `app/models/schemas.py` — pero sin resignar la validación de longitud
    que ya usan los schemas escritos a mano (ej. `InterpretacionAreasDeVida`),
    que es lo que nos protege de que Claude devuelva un texto demasiado
    corto o demasiado largo y dispare `_validation_error` en producción
    (ver TECH_DEBT.md: ya pasó una vez con `HoroscopoSigno.texto`).

    `secciones` es una lista de dicts con esta forma:
        [{"nombre": "vocacion", "min_chars": 150, "max_chars": 1800, "descripcion": "..."}]

    Cada elemento se convierte en un campo `str` obligatorio del schema
    resultante, vía `Field(..., min_length=min_chars, max_length=max_chars,
    description=descripcion)` — mismo patrón que ya usa `app/models/schemas.py`
    para las llamadas existentes a Claude.

    Lanza `ValueError` si `secciones` viene vacía, o si alguna sección tiene
    `min_chars >= max_chars` (rango de longitud inválido o vacío).
    """
    if not secciones:
        raise ValueError("secciones no puede estar vacío: no hay nada con lo que construir el schema")

    campos = {}
    for seccion in secciones:
        nombre = seccion["nombre"]
        min_chars = seccion["min_chars"]
        max_chars = seccion["max_chars"]
        descripcion = seccion.get("descripcion", "")

        if min_chars >= max_chars:
            raise ValueError(
                f"Sección '{nombre}': min_chars ({min_chars}) debe ser menor que max_chars ({max_chars})"
            )

        campos[nombre] = (
            str,
            Field(..., min_length=min_chars, max_length=max_chars, description=descripcion),
        )

    return create_model(nombre_schema, **campos)
