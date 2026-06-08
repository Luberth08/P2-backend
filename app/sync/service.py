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
from app.core.timezone import now_bolivia, parse_iso_to_bolivia
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
            error_msg = str(e)
            logger.error(f"Error ejecutando operación para {item.client_sync_id}: {error_msg}")
            
            # Verificar si es un error de duplicado (unique constraint violation)
            if 'unique constraint' in error_msg.lower() or 'duplicate' in error_msg.lower():
                logger.warning(f"Duplicado detectado para {item.client_sync_id}, marcando como success")
                await self._log_sync_operation(
                    item,
                    user_id,
                    ip_address,
                    status="success",
                    server_entity_id=None,
                    error_message=f"Duplicado (ignorado): {error_msg}"
                )
                # Retornar success para evitar reintento
                return SyncItemResult(
                    client_sync_id=item.client_sync_id,
                    status="success",
                    error_message="Item ya existe (duplicado)"
                )
            
            # Para otros errores, registrar y lanzar
            await self._log_sync_operation(
                item,
                user_id,
                ip_address,
                status="error",
                server_entity_id=None,
                error_message=error_msg
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
        # Crear una copia mutable del payload para no modificar el original
        payload = dict(item.payload) if item.payload else {}
        
        logger.info(f"Creating entity {item.entity_type} with payload: {payload}")
        
        try:
            if item.entity_type == EntityType.solicitud_servicio:
                # Mapear fecha_solicitud a fecha si existe
                if 'fecha_solicitud' in payload:
                    payload['fecha'] = payload.pop('fecha_solicitud')
                
                # Agregar fecha si no existe
                if 'fecha' not in payload:
                    payload['fecha'] = now_bolivia()
                
                # Convertir fecha a datetime si es string
                if isinstance(payload.get('fecha'), str):
                    payload['fecha'] = parse_iso_to_bolivia(payload['fecha'])
                
                # Validar campos requeridos
                if 'id_diagnostico' not in payload:
                    raise ValueError("id_diagnostico es requerido para solicitud_servicio")
                if 'id_taller' not in payload:
                    raise ValueError("id_taller es requerido para solicitud_servicio")
                if 'sugerido_por' not in payload:
                    payload['sugerido_por'] = 'conductor'  # Default
                
                # Verificar que existan las foreign keys
                from app.models.diagnostico import Diagnostico
                from app.models.taller import Taller
                
                diagnostico = await self.db.get(Diagnostico, payload['id_diagnostico'])
                if not diagnostico:
                    raise ValueError(f"No existe diagnóstico con id {payload['id_diagnostico']}")
                
                taller = await self.db.get(Taller, payload['id_taller'])
                if not taller:
                    raise ValueError(f"No existe taller con id {payload['id_taller']}")
                
                entity = await solicitud_servicio_crud.create(self.db, payload)
                return entity.id
                
            elif item.entity_type == EntityType.diagnostico:
                entity = await diagnostico_crud.create(self.db, payload)
                return entity.id
                
            elif item.entity_type == EntityType.servicio:
                # Extraer tecnicos_ids y vehiculos_ids (no son parte del modelo)
                tecnicos_ids = payload.pop('tecnicos_ids', [])
                vehiculos_ids = payload.pop('vehiculos_ids', [])
                
                # Validar campos requeridos
                if 'id_taller' not in payload:
                    raise ValueError("id_taller es requerido para servicio")
                if 'id_solicitud_servicio' not in payload:
                    raise ValueError("id_solicitud_servicio es requerido para servicio")
                
                # DUPLICATE DETECTION: Verificar si ya existe un servicio para esta solicitud
                from app.models.servicio import Servicio
                try:
                    existing_query = await self.db.execute(
                        select(Servicio).where(
                            and_(
                                Servicio.id_solicitud_servicio == payload['id_solicitud_servicio'],
                                Servicio.id_taller == payload['id_taller']
                            )
                        )
                    )
                    existing_service = existing_query.scalar_one_or_none()
                    
                    if existing_service:
                        logger.info(f"✅ Servicio ya existe para solicitud {payload['id_solicitud_servicio']}, taller {payload['id_taller']}, retornando id existente: {existing_service.id}")
                        return existing_service.id
                except Exception as e:
                    logger.error(f"Error verificando servicio existente: {e}")
                
                # Agregar defaults
                if 'fecha' not in payload:
                    payload['fecha'] = now_bolivia()
                if 'estado' not in payload:
                    payload['estado'] = 'creado'
                
                # Crear el servicio
                entity = await servicio_crud.create(self.db, payload)
                
                # IMPORTANTE: Actualizar estado de la solicitud a "aceptada"
                from app.models.solicitud_servicio import EstadoSolicitudServicio
                from app.crud import solicitud_servicio as solicitud_servicio_crud
                try:
                    await solicitud_servicio_crud.update_estado(
                        self.db,
                        payload['id_solicitud_servicio'],
                        EstadoSolicitudServicio.aceptada
                    )
                    logger.info(f"Estado de solicitud {payload['id_solicitud_servicio']} actualizado a 'aceptada'")
                except Exception as e:
                    logger.warning(f"No se pudo actualizar estado de solicitud: {e}")
                
                # Asignar técnicos si se proporcionaron
                if tecnicos_ids:
                    from app.models.servicio_tecnico import ServicioTecnico
                    from app.models.empleado import EstadoEmpleado
                    from app.crud import empleado as empleado_crud
                    
                    for tecnico_id in tecnicos_ids:
                        # Verificar si ya existe la asignación
                        existing_tecnico_query = await self.db.execute(
                            select(ServicioTecnico).where(
                                and_(
                                    ServicioTecnico.id_servicio == entity.id,
                                    ServicioTecnico.id_empleado == tecnico_id
                                )
                            )
                        )
                        existing_tecnico = existing_tecnico_query.scalar_one_or_none()
                        
                        if not existing_tecnico:
                            servicio_tecnico = ServicioTecnico(
                                id_servicio=entity.id,
                                id_empleado=tecnico_id
                            )
                            self.db.add(servicio_tecnico)
                            
                            # Actualizar estado del técnico a "en_servicio"
                            try:
                                empleado = await empleado_crud.get(self.db, tecnico_id)
                                if empleado and empleado.estado == EstadoEmpleado.disponible:
                                    empleado.estado = EstadoEmpleado.en_servicio
                                    logger.info(f"Estado de técnico {tecnico_id} actualizado a 'en_servicio'")
                            except Exception as e:
                                logger.warning(f"No se pudo actualizar estado de técnico {tecnico_id}: {e}")
                    
                    await self.db.flush()
                
                # Asignar vehículos si se proporcionaron
                if vehiculos_ids:
                    from app.models.servicio_vehiculo import ServicioVehiculo
                    from app.models.vehiculo_taller import EstadoVehiculoTaller, VehiculoTaller
                    
                    for vehiculo_id in vehiculos_ids:
                        # Verificar si ya existe la asignación
                        existing_vehiculo_query = await self.db.execute(
                            select(ServicioVehiculo).where(
                                and_(
                                    ServicioVehiculo.id_servicio == entity.id,
                                    ServicioVehiculo.id_vehiculo_taller == vehiculo_id
                                )
                            )
                        )
                        existing_vehiculo = existing_vehiculo_query.scalar_one_or_none()
                        
                        if not existing_vehiculo:
                            servicio_vehiculo = ServicioVehiculo(
                                id_servicio=entity.id,
                                id_vehiculo_taller=vehiculo_id
                            )
                            self.db.add(servicio_vehiculo)
                            
                            # Actualizar estado del vehículo a "en_servicio"
                            try:
                                vehiculo_query = await self.db.execute(
                                    select(VehiculoTaller).where(VehiculoTaller.id == vehiculo_id)
                                )
                                vehiculo = vehiculo_query.scalar_one_or_none()
                                if vehiculo and vehiculo.estado == EstadoVehiculoTaller.disponible:
                                    vehiculo.estado = EstadoVehiculoTaller.en_servicio
                                    logger.info(f"Estado de vehículo {vehiculo_id} actualizado a 'en_servicio'")
                            except Exception as e:
                                logger.warning(f"No se pudo actualizar estado de vehículo {vehiculo_id}: {e}")
                    
                    await self.db.flush()
                
                logger.info(f"Servicio {entity.id} creado con {len(tecnicos_ids)} técnicos y {len(vehiculos_ids)} vehículos")
                return entity.id
                
            elif item.entity_type == EntityType.incidente:
                entity = await incidente_crud.create(self.db, payload)
                # Incidente tiene clave compuesta, retornamos el id_diagnostico
                return entity.id_diagnostico
            else:
                raise ValueError(f"Tipo de entidad no soportado: {item.entity_type}")
        except Exception as e:
            logger.error(f"Error creando entidad {item.entity_type}: {str(e)}, payload: {payload}")
            raise
    
    async def _update_entity(self, item: SyncItem) -> int:
        """Actualiza una entidad según su tipo"""
        payload = item.payload
        entity_id = item.entity_id
        
        if not entity_id:
            raise ValueError("Se requiere entity_id para operaciones de update")
        
        # Primero obtenemos la entidad existente
        if item.entity_type == EntityType.solicitud_servicio:
            db_obj = await solicitud_servicio_crud.get(self.db, entity_id)
            if not db_obj:
                raise ValueError(f"SolicitudServicio con id {entity_id} no encontrada")
            entity = await solicitud_servicio_crud.update(self.db, db_obj, payload)
            return entity.id
        elif item.entity_type == EntityType.diagnostico:
            db_obj = await diagnostico_crud.get(self.db, entity_id)
            if not db_obj:
                raise ValueError(f"Diagnostico con id {entity_id} no encontrado")
            entity = await diagnostico_crud.update(self.db, db_obj, payload)
            return entity.id
        elif item.entity_type == EntityType.servicio:
            db_obj = await servicio_crud.get(self.db, entity_id)
            if not db_obj:
                raise ValueError(f"Servicio con id {entity_id} no encontrado")
            entity = await servicio_crud.update(self.db, db_obj, payload)
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
        # Convertir client_timestamp a naive datetime si tiene timezone
        client_ts = item.client_timestamp
        if client_ts and hasattr(client_ts, 'tzinfo') and client_ts.tzinfo is not None:
            client_ts = client_ts.replace(tzinfo=None)
        
        log_entry = SyncLog(
            operation_type=item.operation_type,
            entity_type=item.entity_type,
            client_sync_id=item.client_sync_id,
            server_entity_id=server_entity_id,
            status=status,
            error_message=error_message,
            client_timestamp=client_ts,
            server_timestamp=now_bolivia(),
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
