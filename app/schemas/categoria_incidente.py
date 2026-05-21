from pydantic import BaseModel, field_validator
from typing import List


class CategoriaIncidenteBase(BaseModel):
    nombre: str


class CategoriaIncidenteCreate(CategoriaIncidenteBase):
    especialidad_ids: List[int]
    
    @field_validator('especialidad_ids')
    @classmethod
    def validate_especialidades(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Debe seleccionar al menos una especialidad')
        return v


class CategoriaIncidenteUpdate(BaseModel):
    nombre: str | None = None
    especialidad_ids: List[int] | None = None
    
    @field_validator('especialidad_ids')
    @classmethod
    def validate_especialidades(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError('Debe mantener al menos una especialidad')
        return v


class CategoriaIncidenteResponse(CategoriaIncidenteBase):
    id: int
    especialidad_ids: List[int] = []

    class Config:
        from_attributes = True


class CategoriaIncidenteListResponse(BaseModel):
    items: List[CategoriaIncidenteResponse]
    total: int
    skip: int
    limit: int
