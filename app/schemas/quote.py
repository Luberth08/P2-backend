from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class QuoteItemCreate(BaseModel):
    titulo: str = Field(..., max_length=200)
    precio: Decimal = Field(..., ge=0)

    class Config:
        orm_mode = True


class QuoteItemResponse(BaseModel):
    id: int
    titulo: str
    precio: Decimal

    class Config:
        orm_mode = True


class QuoteResponseCreate(BaseModel):
    items: List[QuoteItemCreate]

    class Config:
        orm_mode = True


class QuoteResponseResponse(BaseModel):
    id: int
    fecha_creacion: datetime
    fecha_respuesta: Optional[datetime] = None
    estado: str
    total: Optional[Decimal] = None
    id_quote_request: int
    id_taller: int
    items: List[QuoteItemResponse] = []

    class Config:
        orm_mode = True


class TallerBasicInfo(BaseModel):
    id: int
    nombre: str
    telefono: str
    email: str

    class Config:
        orm_mode = True


class ServicioBasicInfo(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None

    class Config:
        orm_mode = True


class VehiculoBasicInfo(BaseModel):
    id: int
    placa: str
    marca: str
    modelo: str

    class Config:
        orm_mode = True


class QuoteRequestCreate(BaseModel):
    id_vehiculo: int
    id_servicio: int
    ubicacion_lat: Optional[float] = None
    ubicacion_lon: Optional[float] = None
    comentario: Optional[str] = Field(None, max_length=500)
    ids_talleres: List[int] = Field(..., min_items=1)

    class Config:
        orm_mode = True


class QuoteRequestResponse(BaseModel):
    id: int
    ubicacion: Optional[str] = None  # "lat,lon"
    fecha_creacion: datetime
    fecha_expiracion: Optional[datetime] = None
    comentario: Optional[str] = None
    estado: str
    fecha_aceptada: Optional[datetime] = None
    id_vehiculo: int
    id_servicio: int
    id_cliente: int
    vehiculo: Optional[VehiculoBasicInfo] = None
    servicio: Optional[ServicioBasicInfo] = None
    responses: List[QuoteResponseResponse] = []
    fotos: Optional[List[str]] = None  # URLs de las fotos

    class Config:
        orm_mode = True


class QuoteRequestListResponse(BaseModel):
    items: List[QuoteRequestResponse]
    total: int
    skip: int
    limit: int


class QuoteAcceptRequest(BaseModel):
    id_quote_response: int

    class Config:
        orm_mode = True


class TallerQuoteRequestResponse(BaseModel):
    """Respuesta que ve el taller para una solicitud de cotización"""
    id: int
    ubicacion: Optional[str] = None
    fecha_creacion: datetime
    fecha_expiracion: Optional[datetime] = None
    comentario: Optional[str] = None
    estado: str
    vehiculo: Optional[VehiculoBasicInfo] = None
    servicio: Optional[ServicioBasicInfo] = None
    cliente_nombre: Optional[str] = None
    ya_respondio: bool = False
    mi_respuesta: Optional[QuoteResponseResponse] = None
    fotos: Optional[List[str]] = None  # URLs de las fotos

    class Config:
        orm_mode = True


class TallerQuoteRequestListResponse(BaseModel):
    items: List[TallerQuoteRequestResponse]
    total: int
    skip: int
    limit: int
