from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# Importar función para obtener hora de Bolivia
def _now_bolivia():
    """Importación lazy para evitar circular imports"""
    from app.core.timezone import now_bolivia
    return now_bolivia()


class OperationType(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"


class EntityType(str, Enum):
    solicitud_servicio = "solicitud_servicio"
    diagnostico = "diagnostico"
    servicio = "servicio"
    incidente = "incidente"


class SyncItem(BaseModel):
    """Item individual de sincronización"""
    operation_type: OperationType
    entity_type: EntityType
    client_sync_id: str = Field(..., description="ID único del cliente para evitar duplicados")
    entity_id: Optional[int] = Field(None, description="ID local del cliente (si existe)")
    payload: Dict[str, Any] = Field(..., description="Datos completos de la entidad")
    client_timestamp: Optional[datetime] = Field(None, description="Timestamp del cliente")


class SyncRequest(BaseModel):
    """Request de sincronización desde el cliente"""
    items: List[SyncItem] = Field(..., description="Lista de items a sincronizar")
    user_id: Optional[int] = Field(None, description="ID del usuario (si está autenticado)")
    device_info: Optional[Dict[str, Any]] = Field(None, description="Información del dispositivo")


class SyncItemResult(BaseModel):
    """Resultado de sincronización de un item"""
    client_sync_id: str
    status: str  # success, conflict, error
    server_entity_id: Optional[int] = None
    error_message: Optional[str] = None


class SyncResponse(BaseModel):
    """Response de sincronización al cliente"""
    success: bool
    total_items: int
    successful_items: int
    failed_items: int
    conflicted_items: int
    results: List[SyncItemResult]
    server_timestamp: datetime = Field(default_factory=_now_bolivia)


class SyncStatusResponse(BaseModel):
    """Estado de sincronización del cliente"""
    pending_items: int
    last_sync_timestamp: Optional[datetime]
    sync_in_progress: bool


class ConflictResolution(BaseModel):
    """Resolución de conflictos"""
    client_sync_id: str
    resolution: str  # "keep_client", "keep_server", "merge"
    merged_payload: Optional[Dict[str, Any]] = None
