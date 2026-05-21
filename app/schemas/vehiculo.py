from pydantic import BaseModel, Field, validator
from typing import Optional
from app.models.vehiculo import TipoVehiculo

class VehiculoBase(BaseModel):
    matricula: str = Field(..., max_length=20, description="Matrícula única del vehículo")
    marca: str = Field(..., max_length=100)
    modelo: str = Field(..., max_length=100)
    anio: int = Field(..., ge=1900, le=2100, description="Año del vehículo (1900-2100)")
    color: Optional[str] = Field(None, max_length=50)
    tipo: TipoVehiculo

    # Validación adicional para matrícula (opcional, por ejemplo formato)
    @validator('matricula')
    def matricula_no_vacia(cls, v):
        if not v.strip():
            raise ValueError('La matrícula no puede estar vacía')
        return v.upper()  # Normalizar a mayúsculas

class VehiculoCreate(VehiculoBase):
    pass

class VehiculoUpdate(BaseModel):
    matricula: Optional[str] = Field(None, max_length=20)
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    anio: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=50)
    tipo: Optional[TipoVehiculo] = None

class VehiculoResponse(VehiculoBase):
    id: int

    class Config:
        from_attributes = True

class VehiculoListResponse(BaseModel):
    items: list[VehiculoResponse]
    total: int
    skip: int
    limit: int