from pydantic import BaseModel, Field
from typing import Optional


class TipoIncidenteBase(BaseModel):
    concepto: str
    prioridad: int = Field(..., ge=1, le=5)
    requiere_remolque: bool = False
    id_categoria_incidente: Optional[int] = None


class TipoIncidenteCreate(TipoIncidenteBase):
    pass


class TipoIncidenteUpdate(BaseModel):
    concepto: Optional[str] = None
    prioridad: Optional[int] = Field(None, ge=1, le=5)
    requiere_remolque: Optional[bool] = None
    id_categoria_incidente: Optional[int] = None


class TipoIncidenteResponse(TipoIncidenteBase):
    id: int
    categoria_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class TipoIncidenteListResponse(BaseModel):
    items: list[TipoIncidenteResponse]
    total: int
    skip: int
    limit: int
