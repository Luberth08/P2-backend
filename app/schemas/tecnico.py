from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.schemas.especialidad import EspecialidadResponse

class TecnicoCreate(BaseModel):
    email: EmailStr
    especialidades_ids: List[int]  # IDs de especialidades seleccionadas

class TecnicoEspecialidadesUpdate(BaseModel):
    especialidades_ids: List[int]

class TecnicoResponse(BaseModel):
    id: int
    usuario_id: int
    usuario_nombre: str
    usuario_email: str
    estado: str  # 'disponible', 'suspendido', etc.
    fecha_ingreso: datetime
    fecha_salida: Optional[datetime] = None
    especialidades: List[EspecialidadResponse] = []

    class Config:
        from_attributes = True

class TecnicoListResponse(BaseModel):
    items: List[TecnicoResponse]
    total: int
    skip: int
    limit: int