from pydantic import BaseModel, Field
from datetime import datetime


class DatosNacimiento(BaseModel):
    fecha_hora_local: datetime = Field(
        ...,
        description="Fecha y hora local de nacimiento, sin zona horaria. Ej: 2000-08-25T14:50:00"
    )
    latitud: float = Field(..., ge=-90, le=90, description="Latitud en grados decimales")
    longitud: float = Field(..., ge=-180, le=180, description="Longitud en grados decimales")


class RespuestaCartaNatal(BaseModel):
    metadata: dict
    calculo: dict