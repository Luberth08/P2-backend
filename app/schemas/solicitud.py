from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

class EstadoSolicitudEnum(str, Enum):
    pendiente = "pendiente"
    aprobada = "aprobada"
    rechazada = "rechazada"

class SolicitudAfiliacionBase(BaseModel):
    nombre: str = Field(..., max_length=100, description="Nombre del taller")
    ubicacion: str = Field(..., description="Ubicación en formato 'lat,lon' (ej: -17.3895,-66.1568)")
    telefono: str = Field(..., max_length=15)
    email: EmailStr
    comentario: Optional[str] = None

class SolicitudAfiliacionCreate(SolicitudAfiliacionBase):
    pass

class SolicitudAfiliacionResponse(SolicitudAfiliacionBase):
    id: int
    fecha: datetime
    fecha_revision: Optional[datetime]
    estado: EstadoSolicitudEnum
    id_usuario_solicita: int
    id_usuario_revisa: Optional[int]
    nombre_usuario_solicita: str
    nombre_usuario_revisa: Optional[str] = None
    comentario_revision: Optional[str] = None

    class Config:
        from_attributes = True

class SolicitudAfiliacionUpdateEstado(BaseModel):
    estado: EstadoSolicitudEnum
    comentario_revision: Optional[str] = None

class SolicitudListResponse(BaseModel):
    items: list[SolicitudAfiliacionResponse]
    total: int
    skip: int
    limit: int