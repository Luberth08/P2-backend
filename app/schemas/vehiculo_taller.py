from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.vehiculo_taller import TipoVehiculoTaller, EstadoVehiculoTaller


class VehiculoTallerBase(BaseModel):
    matricula: str = Field(..., max_length=20, description="Matrícula única del vehículo")
    marca: str = Field(..., max_length=100)
    modelo: str = Field(..., max_length=100)
    anio: int = Field(..., ge=1900, le=2100, description="Año del vehículo (1900-2100)")
    color: Optional[str] = Field(None, max_length=50)
    tipo: TipoVehiculoTaller

    @validator('matricula')
    def matricula_no_vacia(cls, v):
        if not v or not v.strip():
            raise ValueError('La matrícula no puede estar vacía')
        return v.upper()


class VehiculoTallerCreate(VehiculoTallerBase):
    pass


class VehiculoTallerUpdate(BaseModel):
    matricula: Optional[str] = Field(None, max_length=20)
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    anio: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=50)
    tipo: Optional[TipoVehiculoTaller] = None
    estado: Optional[EstadoVehiculoTaller] = None


class VehiculoTallerResponse(VehiculoTallerBase):
    id: int
    estado: EstadoVehiculoTaller
    id_taller: int

    class Config:
        from_attributes = True


class VehiculoTallerListResponse(BaseModel):
    items: List[VehiculoTallerResponse]
    total: int
    skip: int
    limit: int
