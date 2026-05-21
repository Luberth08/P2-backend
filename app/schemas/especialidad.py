from pydantic import BaseModel
from typing import Optional, List


class EspecialidadBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class EspecialidadCreate(EspecialidadBase):
    pass


class EspecialidadUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None


class EspecialidadResponse(EspecialidadBase):
    id: int

    class Config:
        from_attributes = True


class EspecialidadListResponse(BaseModel):
    items: List[EspecialidadResponse]
    total: int
    skip: int
    limit: int