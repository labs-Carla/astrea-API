from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.admin_auth import verificar_admin_secret
from app.api.admin import _iso_utc
from app.models.db_models import ProductoConfig, ProductoGenerado
from app.services.generacion_producto_service import generar_producto
from app.infrastructure.persistence_service import (
    crear_producto_config,
    obtener_producto_config,
    listar_producto_configs,
    actualizar_producto_config,
    obtener_producto_generado_por_id,
    editar_contenido_producto_generado,
    aprobar_producto_generado,
    marcar_producto_enviado,
    listar_productos_generados_pendientes_de_aprobacion,
)

router = APIRouter()


def _serializar_config(config: ProductoConfig) -> dict:
    return {
        "codigo": config.codigo,
        "nombre": config.nombre,
        "system_prompt": config.system_prompt,
        "instrucciones_usuario_template": config.instrucciones_usuario_template,
        "criterios_json": config.criterios_json,
        "temas_a_criterios_json": config.temas_a_criterios_json,
        "secciones_json": config.secciones_json,
        "inputs_requeridos_json": config.inputs_requeridos_json,
        "activo": config.activo,
        "created_at": _iso_utc(config.created_at),
    }


def _serializar_producto_generado(producto_generado: ProductoGenerado) -> dict:
    return {
        "id": producto_generado.id,
        "carta_id": producto_generado.carta_id,
        "producto_codigo": producto_generado.producto_codigo,
        "estado": producto_generado.estado,
        "inputs_json": producto_generado.inputs_json,
        "contenido_json": producto_generado.contenido_json,
        "token": producto_generado.token,
        "fecha_generacion": _iso_utc(producto_generado.fecha_generacion),
        "fecha_aprobacion": _iso_utc(producto_generado.fecha_aprobacion),
        "fecha_envio": _iso_utc(producto_generado.fecha_envio),
    }


class ProductoConfigRequest(BaseModel):
    codigo: str
    nombre: str
    system_prompt: str
    instrucciones_usuario_template: str
    criterios_json: str | None = None
    temas_a_criterios_json: str | None = None
    secciones_json: str
    inputs_requeridos_json: str


class ProductoConfigUpdateRequest(BaseModel):
    nombre: str | None = None
    system_prompt: str | None = None
    instrucciones_usuario_template: str | None = None
    criterios_json: str | None = None
    temas_a_criterios_json: str | None = None
    secciones_json: str | None = None
    inputs_requeridos_json: str | None = None
    activo: bool | None = None


class GenerarProductoRequest(BaseModel):
    carta_id: int
    inputs_adicionales: dict = {}


class EditarContenidoProductoRequest(BaseModel):
    contenido_parcial: dict


@router.post("/admin/producto-configs", dependencies=[Depends(verificar_admin_secret)])
def crear_producto_config_admin(datos: ProductoConfigRequest, db: Session = Depends(get_db)):
    if obtener_producto_config(db, datos.codigo) is not None:
        raise HTTPException(status_code=409, detail=f"Ya existe un producto con código '{datos.codigo}'.")

    config = crear_producto_config(
        db,
        codigo=datos.codigo,
        nombre=datos.nombre,
        system_prompt=datos.system_prompt,
        instrucciones_usuario_template=datos.instrucciones_usuario_template,
        criterios_json=datos.criterios_json,
        temas_a_criterios_json=datos.temas_a_criterios_json,
        secciones_json=datos.secciones_json,
        inputs_requeridos_json=datos.inputs_requeridos_json,
    )
    return _serializar_config(config)


@router.get("/admin/producto-configs", dependencies=[Depends(verificar_admin_secret)])
def listar_producto_configs_admin(solo_activos: bool = True, db: Session = Depends(get_db)):
    configs = listar_producto_configs(db, solo_activos=solo_activos)
    return [_serializar_config(config) for config in configs]


@router.get("/admin/producto-configs/{codigo}", dependencies=[Depends(verificar_admin_secret)])
def ver_producto_config_admin(codigo: str, db: Session = Depends(get_db)):
    config = obtener_producto_config(db, codigo)

    if config is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    return _serializar_config(config)


@router.patch("/admin/producto-configs/{codigo}", dependencies=[Depends(verificar_admin_secret)])
def editar_producto_config_admin(codigo: str, datos: ProductoConfigUpdateRequest, db: Session = Depends(get_db)):
    config = obtener_producto_config(db, codigo)

    if config is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    # exclude_unset (no exclude_none): un PATCH que no menciona un campo lo
    # deja igual; solo se pisa lo que el body efectivamente trae, incluso si
    # el valor nuevo es explícitamente null (ej. "vaciar" criterios_json).
    campos_a_actualizar = datos.model_dump(exclude_unset=True)
    config = actualizar_producto_config(db, config, **campos_a_actualizar)

    return _serializar_config(config)


@router.post("/admin/productos/{codigo}/generar", dependencies=[Depends(verificar_admin_secret)])
async def generar_producto_admin(codigo: str, datos: GenerarProductoRequest, db: Session = Depends(get_db)):
    try:
        producto_generado = await generar_producto(db, datos.carta_id, codigo, datos.inputs_adicionales)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _serializar_producto_generado(producto_generado)


@router.get("/admin/productos-generados/pendientes", dependencies=[Depends(verificar_admin_secret)])
def listar_productos_generados_pendientes_admin(db: Session = Depends(get_db)):
    pendientes = listar_productos_generados_pendientes_de_aprobacion(db)
    return [_serializar_producto_generado(pg) for pg in pendientes]


@router.patch("/admin/productos-generados/{producto_generado_id}", dependencies=[Depends(verificar_admin_secret)])
def editar_producto_generado_admin(
    producto_generado_id: int, datos: EditarContenidoProductoRequest, db: Session = Depends(get_db)
):
    producto_generado = obtener_producto_generado_por_id(db, producto_generado_id)

    if producto_generado is None:
        raise HTTPException(status_code=404, detail="Producto generado no encontrado.")

    try:
        producto_generado = editar_contenido_producto_generado(db, producto_generado, datos.contenido_parcial)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _serializar_producto_generado(producto_generado)


@router.post(
    "/admin/productos-generados/{producto_generado_id}/aprobar",
    dependencies=[Depends(verificar_admin_secret)],
)
def aprobar_producto_generado_admin(producto_generado_id: int, db: Session = Depends(get_db)):
    producto_generado = obtener_producto_generado_por_id(db, producto_generado_id)

    if producto_generado is None:
        raise HTTPException(status_code=404, detail="Producto generado no encontrado.")

    try:
        producto_generado = aprobar_producto_generado(db, producto_generado)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # No arma un link (a diferencia de aprobar_envio para CartaNatalGuardada):
    # todavia no existe una ruta publica que resuelva un token de
    # ProductoGenerado (equivalente a /r/{token} para cartas). Devolver un
    # link armado a mano apuntaria a un endpoint inexistente.
    return {"status": "aprobado", "token": producto_generado.token}


@router.post(
    "/admin/productos-generados/{producto_generado_id}/enviar",
    dependencies=[Depends(verificar_admin_secret)],
)
def enviar_producto_generado_admin(producto_generado_id: int, db: Session = Depends(get_db)):
    """
    Marca un producto aprobado como enviado. Igual que aprobar_envio en
    admin.py, SMTP todavia no esta configurado -- no envia ningun correo,
    devuelve el token para que el admin lo copie a mano (ver nota en
    aprobar_producto_generado_admin sobre la ruta publica pendiente).
    """
    producto_generado = obtener_producto_generado_por_id(db, producto_generado_id)

    if producto_generado is None:
        raise HTTPException(status_code=404, detail="Producto generado no encontrado.")

    try:
        producto_generado = marcar_producto_enviado(db, producto_generado)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"status": "enviado", "token": producto_generado.token}
