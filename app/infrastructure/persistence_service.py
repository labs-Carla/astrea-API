import json
import secrets
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.db_models import CartaNatalGuardada
from app.models.db_models import HoroscopoGenerado
from app.models.db_models import ProductoConfig, ProductoGenerado



def buscar_carta_existente(
    db: Session, fecha_hora_local: datetime, latitud: float, longitud: float
) -> CartaNatalGuardada | None:
    """
    Busca si ya existe una carta generada con estos datos exactos de nacimiento,
    sin importar si tiene resumen, interpretacion completa, o ambos.
    """
    return (
        db.query(CartaNatalGuardada)
        .filter(
            CartaNatalGuardada.fecha_hora_local == fecha_hora_local,
            CartaNatalGuardada.latitud == latitud,
            CartaNatalGuardada.longitud == longitud,
        )
        .first()
    )


def guardar_resumen(
    db: Session,
    fecha_hora_local: datetime,
    latitud: float,
    longitud: float,
    calculo: dict,
    resumen: dict,
) -> CartaNatalGuardada:
    """
    Guarda una carta nueva generada por el flujo gratuito: calculo + resumen,
    sin interpretacion_json (queda None hasta que compre el premium).
    """
    nueva_carta = CartaNatalGuardada(
        fecha_hora_local=fecha_hora_local,
        latitud=latitud,
        longitud=longitud,
        calculo_json=json.dumps(calculo),
        resumen_json=json.dumps(resumen),
        interpretacion_json=None,
    )
    db.add(nueva_carta)
    db.commit()
    db.refresh(nueva_carta)
    return nueva_carta

def guardar_carta_completa(
    db: Session,
    fecha_hora_local: datetime,
    latitud: float,
    longitud: float,
    calculo: dict,
    interpretacion: dict | None,
    nombre_reporte: str | None = None,
    email: str | None = None,
) -> CartaNatalGuardada:
    """
    Guarda una carta nueva. Si interpretacion es None (ej. viene de
    /carta-natal/compra sin IA todavia), queda pendiente para generarse
    despues desde el panel de admin. Si viene con nombre_reporte/email
    (flujo de compra), registra fecha_solicitud_compra automaticamente.
    """
    nueva_carta = CartaNatalGuardada(
        fecha_hora_local=fecha_hora_local,
        latitud=latitud,
        longitud=longitud,
        calculo_json=json.dumps(calculo),
        interpretacion_json=json.dumps(interpretacion) if interpretacion is not None else None,
        resumen_json=None,
        nombre_reporte=nombre_reporte,
        email=email,
        fecha_solicitud_compra=datetime.now(timezone.utc) if (nombre_reporte and email) else None,
    )
    db.add(nueva_carta)
    db.commit()
    db.refresh(nueva_carta)
    return nueva_carta


def actualizar_con_interpretacion(
    db: Session, carta: CartaNatalGuardada, interpretacion: dict
) -> CartaNatalGuardada:
    """
    Actualiza una carta que ya existía (generada por el flujo gratuito) agregando
    la interpretacion_json del premium. El calculo_json existente se reutiliza tal cual
    — no se recalcula Swiss Ephemeris, porque ya se calculó cuando se generó el resumen.
    """
    carta.interpretacion_json = json.dumps(interpretacion)
    db.commit()
    db.refresh(carta)
    return carta


def actualizar_datos_compra(
    db: Session, carta: CartaNatalGuardada, nombre_reporte: str, email: str
) -> CartaNatalGuardada:
    """
    Actualiza una carta ya existente (típicamente generada antes por el flujo
    gratuito) con los datos de la compra premium: nombre_reporte y email,
    necesarios para el envío posterior del link de acceso. Registra tambien
    fecha_solicitud_compra con el momento real de este envio.
    """
    carta.nombre_reporte = nombre_reporte
    carta.email = email
    carta.fecha_solicitud_compra = datetime.now(timezone.utc)
    db.commit()
    db.refresh(carta)
    return carta

def listar_pendientes_de_aprobacion(db: Session) -> list[CartaNatalGuardada]:
    """
    Lista las cartas que vienen del flujo de compra (tienen email) y aun no
    han sido aprobadas/enviadas al cliente. Usado por el panel de admin.
    """
    return (
        db.query(CartaNatalGuardada)
        .filter(
            CartaNatalGuardada.email.isnot(None),
            CartaNatalGuardada.enviado.is_(False),
        )
        .order_by(CartaNatalGuardada.fecha_generacion.desc())
        .all()
    )


def obtener_carta_por_id(db: Session, carta_id: int) -> CartaNatalGuardada | None:
    """
    Busca una carta por su id (usado por el panel de admin para ver el
    detalle antes de aprobar el envio).
    """
    return db.query(CartaNatalGuardada).filter(CartaNatalGuardada.id == carta_id).first()


def deserializar_carta(carta: CartaNatalGuardada) -> tuple[dict, dict | None, dict | None]:
    """
    Convierte los campos JSON guardados de vuelta a dicts de Python.
    Retorna (calculo, resumen, interpretacion) — resumen y/o interpretacion
    pueden ser None si esa etapa todavía no se generó para esta carta.
    """
    calculo = json.loads(carta.calculo_json)
    resumen = json.loads(carta.resumen_json) if carta.resumen_json else None
    interpretacion = json.loads(carta.interpretacion_json) if carta.interpretacion_json else None
    return calculo, resumen, interpretacion

def aprobar_y_generar_token(db: Session, carta: CartaNatalGuardada) -> CartaNatalGuardada:
    """
    Genera un token opaco unico para acceso sin login (tipo Notion/Loom),
    lo asigna a la carta, y marca enviado=True junto con la fecha de envio.
    """
    carta.token = secrets.token_urlsafe(24)
    carta.enviado = True
    carta.fecha_envio = datetime.now(timezone.utc)
    db.commit()
    db.refresh(carta)
    return carta


def buscar_carta_por_token(db: Session, token: str) -> CartaNatalGuardada | None:
    """
    Busca una carta por su token de acceso publico (usado por el endpoint
    que consume el cliente final via /r/{token}).
    """
    return db.query(CartaNatalGuardada).filter(CartaNatalGuardada.token == token).first()

def actualizar_genero(db: Session, carta: CartaNatalGuardada, genero: str) -> CartaNatalGuardada:
    """
    Actualiza el campo genero de una carta existente, usado para ajustar la
    concordancia de genero en espanol en ambas llamadas a Claude.
    """
    carta.genero = genero
    db.commit()
    db.refresh(carta)
    return carta


def guardar_areas_de_vida(db: Session, carta: CartaNatalGuardada, areas_de_vida: dict) -> CartaNatalGuardada:
    """
    Guarda el resultado de la segunda llamada a Claude (vocacion, dinero,
    amor, herida/don, aspectos interpretados, plan de accion, brujula).
    """
    carta.areas_de_vida_json = json.dumps(areas_de_vida)
    db.commit()
    db.refresh(carta)
    return carta


def obtener_areas_de_vida(carta: CartaNatalGuardada) -> dict | None:
    """
    Deserializa areas_de_vida_json de vuelta a dict. Funcion separada de
    deserializar_carta a proposito, para no cambiar su firma existente.
    """
    return json.loads(carta.areas_de_vida_json) if carta.areas_de_vida_json else None

def guardar_transitos(db: Session, carta: CartaNatalGuardada, transitos: dict) -> CartaNatalGuardada:
    """
    Guarda el resultado de la tercera llamada a Claude (clima energetico
    actual y proximos meses). Es una foto fija del momento de aprobacion.
    """
    carta.transitos_json = json.dumps(transitos)
    db.commit()
    db.refresh(carta)
    return carta


def obtener_transitos(carta: CartaNatalGuardada) -> dict | None:
    """
    Deserializa transitos_json de vuelta a dict.
    """
    return json.loads(carta.transitos_json) if carta.transitos_json else None

def guardar_horoscopo(db: Session, cadencia: str, fecha: datetime, contenido: dict) -> HoroscopoGenerado:
    """
    Guarda un horoscopo generico generado (diario o semanal) para una fecha
    especifica. No sobrescribe registros anteriores — cada generacion queda
    como su propia fila, permitiendo ver el historial si se quiere.
    """
    nuevo = HoroscopoGenerado(
        cadencia=cadencia,
        fecha=fecha,
        contenido_json=json.dumps(contenido),
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def obtener_horoscopo_mas_reciente(db: Session, cadencia: str) -> HoroscopoGenerado | None:
    """
    Devuelve el horoscopo mas reciente de una cadencia dada (diario o
    semanal), usado para servir el contenido ya generado sin regenerarlo
    en cada visita.
    """
    return (
        db.query(HoroscopoGenerado)
        .filter(HoroscopoGenerado.cadencia == cadencia)
        .order_by(HoroscopoGenerado.fecha.desc())
        .first()
    )


def crear_producto_config(
    db: Session,
    codigo: str,
    nombre: str,
    system_prompt: str,
    instrucciones_usuario_template: str,
    criterios_json: str | None,
    temas_a_criterios_json: str | None,
    secciones_json: str,
    inputs_requeridos_json: str,
) -> ProductoConfig:
    """
    Da de alta un producto/reporte nuevo. A diferencia de guardar_resumen o
    guardar_carta_completa (que reciben dicts de Python y los serializan acá
    con json.dumps), acá los parametros ya vienen serializados por el caller
    (el body crudo del POST /admin/producto-configs) — esta función no
    reinterpreta esos datos, solo los persiste tal cual.
    """
    nuevo = ProductoConfig(
        codigo=codigo,
        nombre=nombre,
        system_prompt=system_prompt,
        instrucciones_usuario_template=instrucciones_usuario_template,
        criterios_json=criterios_json,
        temas_a_criterios_json=temas_a_criterios_json,
        secciones_json=secciones_json,
        inputs_requeridos_json=inputs_requeridos_json,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def obtener_producto_config(db: Session, codigo: str) -> ProductoConfig | None:
    """
    Busca un producto configurado por su codigo (usado antes de generar una
    instancia con generacion_producto_service.generar_producto).
    """
    return db.query(ProductoConfig).filter(ProductoConfig.codigo == codigo).first()


def listar_producto_configs(db: Session, solo_activos: bool = True) -> list[ProductoConfig]:
    """
    Lista los productos configurados. Por default solo los activos —
    desactivar un producto (activo=False) lo saca de esta lista sin borrar
    su fila ni las instancias ya generadas con esa config.
    """
    query = db.query(ProductoConfig)
    if solo_activos:
        query = query.filter(ProductoConfig.activo.is_(True))
    return query.order_by(ProductoConfig.nombre).all()


def actualizar_producto_config(db: Session, config: ProductoConfig, **campos_a_actualizar) -> ProductoConfig:
    """
    Actualiza parcialmente un ProductoConfig existente: solo pisa los
    campos pasados en campos_a_actualizar, deja el resto igual. Usado por
    PATCH /admin/producto-configs/{codigo} para editar, por ejemplo, solo
    el system_prompt sin tener que reenviar la config completa.
    """
    for campo, valor in campos_a_actualizar.items():
        setattr(config, campo, valor)
    db.commit()
    db.refresh(config)
    return config


def crear_producto_generado(db: Session, carta_id: int, producto_codigo: str, inputs_json: str) -> ProductoGenerado:
    """
    Crea la fila de una nueva instancia de un producto para una carta, en
    estado "pendiente" — todavía no se llamó a Claude. Mismo criterio que
    crear_producto_config: inputs_json ya viene serializado por el caller
    (generacion_producto_service), esta función solo lo persiste.
    """
    nuevo = ProductoGenerado(
        carta_id=carta_id,
        producto_codigo=producto_codigo,
        inputs_json=inputs_json,
        estado="pendiente",
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def guardar_contenido_producto_generado(
    db: Session, producto_generado: ProductoGenerado, contenido: dict
) -> ProductoGenerado:
    """
    Guarda el resultado de la llamada a Claude para este producto. Si
    contenido trae "_validation_error" (mismo patrón de fallback que las 5
    llamadas de interpretation_*.py, vía interpretation_common._parsear_respuesta),
    el estado queda en "fallido" en vez de "generado" — se persiste igual,
    para poder inspeccionar la respuesta cruda desde el panel de admin sin
    perderla ni tener que volver a pagar la llamada.
    """
    producto_generado.contenido_json = json.dumps(contenido)
    producto_generado.fecha_generacion = datetime.now(timezone.utc)
    producto_generado.estado = "fallido" if "_validation_error" in contenido else "generado"
    db.commit()
    db.refresh(producto_generado)
    return producto_generado


def editar_contenido_producto_generado(
    db: Session, producto_generado: ProductoGenerado, contenido_parcial: dict
) -> ProductoGenerado:
    """
    Mergea contenido_parcial sobre el contenido_json ya guardado, sin pisar
    las secciones que el edit no incluye (ej. editar solo "vocacion" no debe
    borrar "dinero"). Rechaza la edición si el producto ya está aprobado o
    enviado — en ese punto el contenido ya se le mostró o se le envió al
    cliente con ese texto exacto, editarlo silenciosamente sería inconsistente
    con lo que la persona ya vio.
    """
    if producto_generado.estado in ("aprobado", "enviado"):
        raise ValueError(
            f"No se puede editar un producto en estado '{producto_generado.estado}'"
        )

    contenido_actual = json.loads(producto_generado.contenido_json) if producto_generado.contenido_json else {}
    contenido_actual.update(contenido_parcial)

    producto_generado.contenido_json = json.dumps(contenido_actual)
    producto_generado.estado = "editado"
    db.commit()
    db.refresh(producto_generado)
    return producto_generado


def aprobar_producto_generado(db: Session, producto_generado: ProductoGenerado) -> ProductoGenerado:
    """
    Aprueba un producto ya generado (o editado) y le genera el token opaco
    de acceso sin login, mismo patrón que aprobar_y_generar_token para
    CartaNatalGuardada. Rechaza la aprobación si todavía no hay contenido
    generado o editado que aprobar.
    """
    if producto_generado.estado not in ("generado", "editado"):
        raise ValueError(
            f"No se puede aprobar un producto en estado '{producto_generado.estado}' "
            "-- debe estar 'generado' o 'editado'"
        )

    producto_generado.token = secrets.token_urlsafe(24)
    producto_generado.estado = "aprobado"
    producto_generado.fecha_aprobacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(producto_generado)
    return producto_generado


def marcar_producto_enviado(db: Session, producto_generado: ProductoGenerado) -> ProductoGenerado:
    """
    Marca un producto aprobado como enviado. Rechaza si todavía no fue
    aprobado -- no tiene sentido marcar como enviado algo que nunca se
    aprobó para el cliente.
    """
    if producto_generado.estado != "aprobado":
        raise ValueError(
            f"No se puede marcar como enviado un producto en estado '{producto_generado.estado}' "
            "-- debe estar 'aprobado'"
        )

    producto_generado.estado = "enviado"
    producto_generado.fecha_envio = datetime.now(timezone.utc)
    db.commit()
    db.refresh(producto_generado)
    return producto_generado


def obtener_producto_generado_por_id(db: Session, producto_generado_id: int) -> ProductoGenerado | None:
    """
    Busca una instancia de producto generado por su id (usado por el panel
    de admin para ver el detalle antes de aprobar o editar).
    """
    return db.query(ProductoGenerado).filter(ProductoGenerado.id == producto_generado_id).first()


def listar_productos_generados_pendientes_de_aprobacion(db: Session) -> list[ProductoGenerado]:
    """
    Lista las instancias de producto listas para revisar antes de aprobar
    (generadas o ya editadas, pero todavía no aprobadas ni enviadas) — mismo
    rol que listar_pendientes_de_aprobacion para CartaNatalGuardada.
    """
    return (
        db.query(ProductoGenerado)
        .filter(ProductoGenerado.estado.in_(("generado", "editado")))
        .order_by(ProductoGenerado.fecha_generacion.desc())
        .all()
    )