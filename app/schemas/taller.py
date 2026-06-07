from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import time, datetime


class TallerResponse(BaseModel):
    id: int
    nombre: str
    telefono: str
    email: str
    ubicacion: Optional[str] = None
    estado: str

    class Config:
        from_attributes = True


class TallerDetailResponse(BaseModel):
    """Schema completo con todos los campos del taller"""
    id: int
    nombre: str
    telefono: str
    email: str
    ubicacion: Optional[str] = None
    hora_inicio: Optional[str] = None  # Formato "HH:MM:SS"
    hora_fin: Optional[str] = None     # Formato "HH:MM:SS"
    url_web: Optional[str] = None
    puntos: float
    estado: str

    class Config:
        from_attributes = True


class TallerUpdate(BaseModel):
    """Schema para actualizar información del taller"""
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    ubicacion: Optional[str] = None  # Formato "lat,lon"
    hora_inicio: Optional[str] = None  # Formato "HH:MM" o "HH:MM:SS"
    hora_fin: Optional[str] = None     # Formato "HH:MM" o "HH:MM:SS"
    url_web: Optional[str] = None
    
    @field_validator('ubicacion')
    @classmethod
    def validate_ubicacion(cls, v):
        if v is not None and v.strip():
            parts = v.split(',')
            if len(parts) != 2:
                raise ValueError('Ubicación debe estar en formato "lat,lon"')
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                if not (-90 <= lat <= 90):
                    raise ValueError('Latitud debe estar entre -90 y 90')
                if not (-180 <= lon <= 180):
                    raise ValueError('Longitud debe estar entre -180 y 180')
            except ValueError as e:
                raise ValueError(f'Ubicación inválida: {str(e)}')
        return v
    
    @field_validator('telefono')
    @classmethod
    def validate_telefono(cls, v):
        if v is not None and v.strip():
            # Remover espacios y caracteres especiales comunes
            cleaned = v.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not cleaned.isdigit():
                raise ValueError('Teléfono debe contener solo números')
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValueError('Teléfono debe tener entre 7 y 15 dígitos')
        return v


class ServicioBasicoResponse(BaseModel):
    """Información básica de un servicio para admin sistema"""
    id: int
    fecha: datetime
    estado: str
    
    class Config:
        from_attributes = True


class EmpleadoBasicoResponse(BaseModel):
    """Información básica de un empleado para admin sistema"""
    id: int
    nombre: str
    estado: str
    fecha_ingreso: datetime
    
    class Config:
        from_attributes = True


class TallerAdminDetailResponse(BaseModel):
    """Schema completo para admin sistema con estadísticas"""
    # Información del taller
    id: int
    nombre: str
    telefono: str
    email: str
    ubicacion: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    url_web: Optional[str] = None
    puntos: float
    estado: str
    
    # Estadísticas
    total_servicios: int = 0
    servicios_activos: int = 0
    total_empleados: int = 0
    empleados_activos: int = 0
    
    # Listas resumidas (últimos 5)
    servicios_recientes: List[ServicioBasicoResponse] = []
    empleados_recientes: List[EmpleadoBasicoResponse] = []
    
    class Config:
        from_attributes = True