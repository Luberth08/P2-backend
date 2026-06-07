"""
Servicio de sincronización offline
Maneja la lógica de sincronización de datos cuando los clientes se reconectan
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from app.sync.models import SyncQueue, SyncLog, SyncStatus, OperationType, EntityType
from app.sync.schemas import SyncRequest, SyncItem, SyncItemResult, SyncResponse
from app.crud import (
    solicitud_servicio as solicitud_servicio_crud,
    diagnostico as diagnostico_crud,
    servicio as servicio_crud,
    incidente as incidente_crud
)

logger = logging.getLogger(__name__)


class SyncService:
    """Servicio principal de sincronización"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def process_sync_request(
        self, 
        sync_request: SyncRequest,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> SyncResponse:
        """
        Procesa una solicitud de sincronización desde el cliente
        
        Args:
            sync_request: Request con items a sincronizar
            user_id: ID del usuario autenticado
            ip_address: IP del cliente para logging
            
        Returns:
            SyncResponse con resultados de cada item
        """
        results = []
        successful = 0
        failed = 0
        conflicted = 0
        
        for item in sync_request.items:
            try:
                result = await self._process_sync_item(
                    item, 
                    user_id, 
                    ip_address
                )
                results.append(result)
                
                if result.status == "success":
                    successful += 1
                elif result.status == "conflict":
                    conflicted += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error procesando item {item.client_sync_id}: {e}")
                results.append(SyncItemResult(
                    client_sync_id=item.client_sync_id,
                    status="error",
                    error_message=str(e)
                ))
                failed += 1
        
        await self.db.commit()
        
        return SyncResponse(
            success=failed == 0,
            total_items=len(sync_request.items),
            successful_items=successful,
            failed_items=failed,
            conflicted_items=conflicted,
            results=results
        )
    
    async def _process_sync_item(
        self,
        item: SyncItem,
        user_id: Optional[int],
        ip_address: Optional[str]
    ) -> SyncItemResult:
        """
        Procesa un item individual de sincronización
        
        Args:
            item: Item a sincronizar
            user_id: ID del usuario
            ip_address: IP del cliente
            
        Returns:
            SyncItemResult con el resultado
        """
        # 1. Verificar si ya existe este client_sync_id (evitar duplicados)
        existing_log = await self._get_existing_sync_log(item.client_sync_id)
        if existing_log:
            logger.info(f"Item {item.client_sync_id} ya fue sincronizado anteriormente")
            return SyncItemResult(
                client_sync_id=item.client_sync_id,
                status="success",
                server_entity_id=existing_log.server_entity_id
            )
        
        # 2. Verificar conflictos basados en timestamps
        conflict = await self._check_conflicts(item)
        if conflict:
            logger.warning(f"Conflicto detectado para item {item.client_sync_id}")
            await self._log_sync_operation(
                item, 
                user_id, 
                ip_address, 
                status="conflict",
                server_entity_id=None
            )
            return SyncItemResult(
                client_sync_id=item.client_sync_id,
                status="conflict",
                error_message="Conflicto de datos: el registro fue modificado en el servidor"
            )
        
        # 3. Procesar según tipo de operación
        try:
            server_entity_id = await self._execute_operation(item)
            
            # 4. Log de operación exitosa
            await self._log_sync_operation(
                item,
                user_id,
                ip_address,
                status="success",
                server_entity_id=server_entity_id
            )
            
            return SyncItemResult(
                client_sync_id=item.client_sync_id,
                status="success",
                server_entity_id=server_entity_id
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando operación para {item.client_sync_id}: {e}")
            await self._log_sync_operation(
                item,
                user_id,
                ip_address,
                status="error",
                server_entity_id=None,
                error_message=str(e)
            )
            raise
    
    async def _get_existing_sync_log(self, client_sync_id: str) -> Optional[SyncLog]:
        """Verifica si ya existe un log de sincronización para este client_sync_id"""
        result = await self.db.execute(
            select(SyncLog).where(
                SyncLog.client_sync_id == client_sync_id,
                SyncLog.status == "success"
            )
        )
        return result.scalar_one_or_none()
    
    async def _check_conflicts(self, item: SyncItem) -> bool:
        """
        Verifica si hay conflictos basados en timestamps
        Por ahora simplificado: se puede expandir según necesidad
        """
        # Implementación básica: verificar si la entidad existe y fue modificada
        # después del client_timestamp del item
        if item.client_timestamp is None:
            return False
        
        # Aquí se puede implementar lógica más compleja de detección de conflictos
        # Por ahora retornamos False para permitir la sincronización
        return False
    
    async def _execute_operation(self, item: SyncItem) -> int:
        """
        Ejecuta la operación (create/update/delete) según el tipo de entidad
        """
        if item.operation_type == OperationType.create:
            return await self._create_entity(item)
        elif item.operation_type == OperationType.update:
            return await self._update_entity(item)
        elif item.operation_type == OperationType.delete:
            return await self._delete_entity(item)
        else:
            raise ValueError(f"Operación no soportada: {item.operation_type}")
    
    async def _create_entity(self, item: SyncItem) -> int:
        """Crea una entidad según su tipo"""
        payload = item.payload
        
        if item.entity_type == EntityType.solicitud_servicio:
            entity = await solicitud_servicio_crud.create(self.db, payload)
            return entity.id
        elif item.entity_type == EntityType.diagnostico:
            entity = await diagnostico_crud.create(self.db, payload)
            return entity.id
        elif item.entity_type == EntityType.servicio:
            entity = await servicio_crud.create(self.db, payload)
            return entity.id
        elif item.entity_type == EntityType.incidente:
            entity = await incidente_crud.create(self.db, payload)
            # Incidente tiene clave compuesta, retornamos el id_diagnostico
            return entity.id_diagnostico
        else:
            raise ValueError(f"Tipo de entidad no soportado: {item.entity_type}")
    
    async def _update_entity(self, item: SyncItem) -> int:
        """Actualiza una entidad según su tipo"""
        payload = item.payload
        entity_id = item.entity_id
        
        if not entity_id:
            raise ValueError("Se requiere entity_id para operaciones de update")
        
        if item.entity_type == EntityType.solicitud_servicio:
            entity = await solicitud_servicio_crud.update(self.db, entity_id, payload)
            return entity.id
        elif item.entity_type == EntityType.diagnostico:
            entity = await diagnostico_crud.update(self.db, entity_id, payload)
            return entity.id
        elif item.entity_type == EntityType.servicio:
            entity = await servicio_crud.update(self.db, entity_id, payload)
            return entity.id
        else:
            raise ValueError(f"Update no soportado para entidad: {item.entity_type}")
    
    async def _delete_entity(self, item: SyncItem) -> int:
        """Elimina una entidad según su tipo"""
        entity_id = item.entity_id
        
        if not entity_id:
            raise ValueError("Se requiere entity_id para operaciones de delete")
        
        if item.entity_type == EntityType.solicitud_servicio:
            await solicitud_servicio_crud.delete(self.db, entity_id)
            return entity_id
        elif item.entity_type == EntityType.diagnostico:
            await diagnostico_crud.delete(self.db, entity_id)
            return entity_id
        elif item.entity_type == EntityType.servicio:
            await servicio_crud.delete(self.db, entity_id)
            return entity_id
        else:
            raise ValueError(f"Delete no soportado para entidad: {item.entity_type}")
    
    async def _log_sync_operation(
        self,
        item: SyncItem,
        user_id: Optional[int],
        ip_address: Optional[str],
        status: str,
        server_entity_id: Optional[int],
        error_message: Optional[str] = None
    ):
        """Registra la operación de sincronización en el log"""
        log_entry = SyncLog(
            operation_type=item.operation_type,
            entity_type=item.entity_type,
            client_sync_id=item.client_sync_id,
            server_entity_id=server_entity_id,
            status=status,
            error_message=error_message,
            client_timestamp=item.client_timestamp,
            server_timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address
        )
        self.db.add(log_entry)
        await self.db.flush()
    
    async def get_pending_sync_count(self, user_id: Optional[int] = None) -> int:
        """Obtiene el count de items pendientes de sincronización"""
        query = select(SyncQueue).where(SyncQueue.status == SyncStatus.pending)
        if user_id:
            query = query.where(SyncQueue.user_id == user_id)
        
        result = await self.db.execute(query)
        return len(result.all())
    
    async def get_sync_status(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtiene el estado general de sincronización"""
        pending_count = await self.get_pending_sync_count(user_id)
        
        # Obtener último sync exitoso
        query = select(SyncLog).where(SyncLog.status == "success")
        if user_id:
            query = query.where(SyncLog.user_id == user_id)
        query = query.order_by(SyncLog.server_timestamp.desc()).limit(1)
        
        result = await self.db.execute(query)
        last_sync = result.scalar_one_or_none()
        
        return {
            "pending_items": pending_count,
            "last_sync_timestamp": last_sync.server_timestamp if last_sync else None,
            "sync_in_progress": pending_count > 0
        }


# Función helper para crear instancia del servicio
def get_sync_service(db: AsyncSession) -> SyncService:
    """Crea una instancia del servicio de sincronización"""
    return SyncService(db)
