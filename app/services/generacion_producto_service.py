import json
from anthropic import AsyncAnthropic
from sqlalchemy.orm import Session

from app.models.db_models import ProductoConfig, ProductoGenerado
from app.services.interpretation_common import _client_default, _parsear_respuesta, _log_uso_claude
from app.domain.foco_astrologico_service import extraer_foco
from app.domain.schema_dinamico_service import construir_schema
from app.infrastructure.persistence_service import (
    obtener_producto_config,
    obtener_carta_por_id,
    deserializar_carta,
    crear_producto_generado,
    guardar_contenido_producto_generado,
)


def resolver_criterios(config: ProductoConfig, inputs_adicionales: dict) -> dict:
    """
    Resuelve qué criterios de foco_astrologico_service.extraer_foco usar para
    este producto. Un ProductoConfig declara UNA de dos formas de decidirlo
    (nunca ambas a la vez tienen sentido, pero si config.criterios_json está
    seteado gana siempre, por ser el caso más simple y explícito):

    - criterios_json: el producto siempre usa el mismo foco (ej. un "Reporte
      de vocación" siempre mira Casa 10/MC). Se usa tal cual.
    - temas_a_criterios_json: el producto ofrece varios temas posibles (ej.
      un "Mini reporte a medida" donde el cliente elige "amor" o "dinero"),
      y el foco depende de inputs_adicionales["tema"]. Lanza ValueError si
      el tema pedido no está en el mapa — mejor fallar acá, con un mensaje
      claro, que dejar que .format() del prompt falle más adelante con un
      KeyError críptico.

    Si el producto no declaró ninguno de los dos, no hay foco: se usa el
    cálculo completo de la carta (extraer_foco con criterios vacíos).
    """
    if config.criterios_json:
        return json.loads(config.criterios_json)

    if config.temas_a_criterios_json:
        temas_a_criterios = json.loads(config.temas_a_criterios_json)
        tema = inputs_adicionales.get("tema")
        if tema not in temas_a_criterios:
            raise ValueError(
                f"El tema '{tema}' no está configurado para el producto '{config.codigo}' "
                f"-- temas disponibles: {sorted(temas_a_criterios.keys())}"
            )
        return temas_a_criterios[tema]

    return {}


async def generar_producto(
    db: Session,
    carta_id: int,
    producto_codigo: str,
    inputs_adicionales: dict,
    client: AsyncAnthropic = _client_default,
) -> ProductoGenerado:
    """
    Genera una instancia de un producto configurado para una carta ya
    calculada: resuelve qué criterios de foco usar (resolver_criterios),
    recorta el cálculo con extraer_foco, arma el schema de validación
    dinámico desde secciones_json (construir_schema), arma el prompt de
    usuario desde instrucciones_usuario_template, llama a Claude, valida la
    respuesta contra ese schema, y persiste el resultado —
    guardar_contenido_producto_generado ya deja el estado en "fallido" si la
    respuesta trae "_validation_error", en vez de que este servicio tenga
    que manejarlo aparte.

    Valida ANTES de llamar a Claude que todos los inputs_requeridos_json del
    producto estén presentes en inputs_adicionales — sin este chequeo, un
    input faltante fallaría recién dentro de
    instrucciones_usuario_template.format(...) con un KeyError que no dice
    qué producto ni qué carta estaba generando, después de ya haber gastado
    la llamada a Claude en el peor caso de orden de ejecución.
    """
    config = obtener_producto_config(db, producto_codigo)
    if config is None:
        raise ValueError(f"No existe un producto configurado con código '{producto_codigo}'")

    carta = obtener_carta_por_id(db, carta_id)
    if carta is None:
        raise ValueError(f"No existe una carta con id {carta_id}")

    inputs_requeridos = json.loads(config.inputs_requeridos_json)
    faltantes = [campo for campo in inputs_requeridos if campo not in inputs_adicionales]
    if faltantes:
        raise ValueError(
            f"Faltan inputs requeridos para el producto '{producto_codigo}': {faltantes}"
        )

    calculo, _, _ = deserializar_carta(carta)
    criterios = resolver_criterios(config, inputs_adicionales)
    foco = extraer_foco(calculo, criterios)

    schema = construir_schema(json.loads(config.secciones_json))
    prompt_usuario = config.instrucciones_usuario_template.format(
        **inputs_adicionales, foco_json=json.dumps(foco)
    )

    producto_generado = crear_producto_generado(
        db, carta_id, producto_codigo, json.dumps(inputs_adicionales)
    )

    respuesta = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        system=config.system_prompt,
        messages=[{"role": "user", "content": prompt_usuario}],
    )

    _log_uso_claude(f"producto:{producto_codigo}", respuesta)
    texto_crudo = respuesta.content[0].text.strip()
    contenido = _parsear_respuesta(texto_crudo, schema)

    return guardar_contenido_producto_generado(db, producto_generado, contenido)
