from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import enum
from datetime import datetime


class OperationType(str, enum.Enum):
    create = "create"
    update = "update"
    delete = "delete"


class EntityType(str, enum.Enum):
    solicitud_servicio = "solicitud_servicio"
    diagnostico = "diagnostico"
    servicio = "servicio"
    incidente = "incidente"


class SyncStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SyncQueue(Base):
    """Cola de operaciones pendientes de sincronización"""
    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, index=True)
    operation_type = Column(SQLEnum(OperationType), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    entity_id = Column(Integer, nullable=True)  # ID local del cliente
    client_sync_id = Column(String(255), nullable=False, unique=True, index=True)  # ID único del cliente para evitar duplicados
    payload = Column(JSON, nullable=False)  # Datos completos de la entidad
    status = Column(SQLEnum(SyncStatus), nullable=False, default=SyncStatus.pending)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    processed_at = Column(TIMESTAMP, nullable=True)
    user_id = Column(Integer, nullable=True)  # Usuario que originó la sync

    __table_args__ = (
        {'schema': 'public'},
    )


class SyncLog(Base):
    """Log de operaciones de sincronización para auditoría"""
    __tablename__ = "sync_log"

    id = Column(Integer, primary_key=True, index=True)
    operation_type = Column(SQLEnum(OperationType), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    client_sync_id = Column(String(255), nullable=False, index=True)
    server_entity_id = Column(Integer, nullable=True)  # ID generado en el servidor
    status = Column(String(50), nullable=False)  # success, conflict, error
    error_message = Column(Text, nullable=True)
    client_timestamp = Column(TIMESTAMP, nullable=True)  # Timestamp del cliente
    server_timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    user_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)

    __table_args__ = (
        {'schema': 'public'},
    )
