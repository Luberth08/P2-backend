from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class EstadoEmpleadoEnum(str, Enum):
    activo = "activo"
    disponible = "disponible"
    en_servicio = "en_servicio"
    suspendido = "suspendido"

class RolTallerEnum(str, Enum):
    admin_taller = "admin_taller"
    super_admin_taller = "super_admin_taller"

class EmpleadoBase(BaseModel):
    email: EmailStr
    rol: RolTallerEnum

class EmpleadoCreate(EmpleadoBase):
    pass

class EmpleadoResponse(BaseModel):
    id: int
    usuario_id: int
    usuario_nombre: str
    usuario_email: str
    rol: Optional[str] = None  # nombre del rol
    fecha_ingreso: datetime
    fecha_salida: Optional[datetime] = None
    estado: EstadoEmpleadoEnum

    class Config:
        from_attributes = True

class EmpleadoListResponse(BaseModel):
    items: list[EmpleadoResponse]
    total: int
    skip: int
    limit: int