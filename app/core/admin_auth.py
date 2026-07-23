from fastapi import Header, HTTPException
from app.core.config import settings


def verificar_admin_secret(x_admin_secret: str = Header(...)) -> None:
    """
    Dependencia de FastAPI que protege los endpoints de administracion.
    Exige un header 'X-Admin-Secret' que debe coincidir exactamente con
    settings.admin_secret (definido en .env / variables de entorno).

    Se usa como: @router.get("/admin/algo", dependencies=[Depends(verificar_admin_secret)])
    """
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail="No autorizado.")