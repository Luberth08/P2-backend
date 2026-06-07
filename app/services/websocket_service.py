"""
Servicio de WebSocket para tiempo real
Maneja conexiones WebSocket, salas y emisión de eventos
"""
import logging
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gestor de conexiones WebSocket activas"""
    
    def __init__(self):
        # Diccionario de conexiones activas: {user_id: Set[websocket]}
        self.active_connections: Dict[int, Set[Any]] = {}
        # Diccionario de salas por servicio: {servicio_id: Set[user_id]}
        self.service_rooms: Dict[int, Set[int]] = {}
        # Mapeo de websocket a user_id: {websocket: user_id}
        self.websocket_to_user: Dict[Any, int] = {}
    
    async def connect(self, websocket: Any, user_id: int):
        """Conecta un usuario y registra su WebSocket"""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.websocket_to_user[websocket] = user_id
        
        logger.info(f"Usuario {user_id} conectado via WebSocket. Total conexiones: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: Any):
        """Desconecta un usuario y limpia sus conexiones"""
        user_id = self.websocket_to_user.get(websocket)
        
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Si no hay más conexiones para este usuario, eliminar del dict
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"Usuario {user_id} completamente desconectado")
        
        # Eliminar del mapeo
        if websocket in self.websocket_to_user:
            del self.websocket_to_user[websocket]
        
        logger.info(f"WebSocket desconectado. Total conexiones: {len(self.active_connections)}")
    
    async def join_service_room(self, user_id: int, servicio_id: int):
        """Une a un usuario a una sala de servicio"""
        if servicio_id not in self.service_rooms:
            self.service_rooms[servicio_id] = set()
        
        self.service_rooms[servicio_id].add(user_id)
        logger.info(f"Usuario {user_id} se unió a sala de servicio {servicio_id}")
    
    async def leave_service_room(self, user_id: int, servicio_id: int):
        """Saca a un usuario de una sala de servicio"""
        if servicio_id in self.service_rooms:
            self.service_rooms[servicio_id].discard(user_id)
            
            # Si no hay más usuarios en la sala, eliminar
            if not self.service_rooms[servicio_id]:
                del self.service_rooms[servicio_id]
                logger.info(f"Sala de servicio {servicio_id} eliminada (vacía)")
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """Envía un mensaje a un usuario específico"""
        if user_id not in self.active_connections:
            logger.warning(f"Usuario {user_id} no tiene conexiones activas")
            return
        
        disconnected_websockets = []
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error enviando mensaje a usuario {user_id}: {e}")
                disconnected_websockets.append(websocket)
        
        # Limpiar websockets desconectados
        for ws in disconnected_websockets:
            await self.disconnect(ws)
    
    async def send_to_service_room(self, servicio_id: int, message: Dict[str, Any]):
        """Envía un mensaje a todos los usuarios en una sala de servicio"""
        if servicio_id not in self.service_rooms:
            logger.warning(f"Sala de servicio {servicio_id} no existe")
            return
        
        for user_id in self.service_rooms[servicio_id]:
            await self.send_to_user(user_id, message)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Envía un mensaje a todos los usuarios conectados"""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)


class WebSocketEventEmitter:
    """Emisor de eventos WebSocket para cambios en el sistema"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def emit_servicio_estado_cambiado(
        self,
        servicio_id: int,
        estado_anterior: str,
        estado_nuevo: str,
        user_id_cliente: Optional[int] = None,
        user_id_taller: Optional[int] = None
    ):
        """Emite evento cuando cambia el estado de un servicio"""
        event = {
            "type": "servicio_estado_cambiado",
            "data": {
                "servicio_id": servicio_id,
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Enviar a la sala del servicio
        await self.connection_manager.send_to_service_room(servicio_id, event)
        
        # También enviar específicamente al cliente si está proporcionado
        if user_id_cliente:
            await self.connection_manager.send_to_user(user_id_cliente, event)
        
        # Enviar al taller si está proporcionado
        if user_id_taller:
            await self.connection_manager.send_to_user(user_id_taller, event)
        
        logger.info(f"Evento emitido: servicio_estado_cambiado para servicio {servicio_id}")
    
    async def emit_solicitud_aceptada(
        self,
        solicitud_id: int,
        servicio_id: int,
        id_taller: int,
        user_id_cliente: int
    ):
        """Emite evento cuando un taller acepta una solicitud"""
        event = {
            "type": "solicitud_aceptada",
            "data": {
                "solicitud_id": solicitud_id,
                "servicio_id": servicio_id,
                "id_taller": id_taller,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Enviar al cliente
        await self.connection_manager.send_to_user(user_id_cliente, event)
        
        # Enviar a la sala del servicio
        await self.connection_manager.send_to_service_room(servicio_id, event)
        
        logger.info(f"Evento emitido: solicitud_aceptada para solicitud {solicitud_id}")
    
    async def emit_solicitud_rechazada(
        self,
        solicitud_id: int,
        id_taller: int,
        user_id_cliente: int
    ):
        """Emite evento cuando un taller rechaza una solicitud"""
        event = {
            "type": "solicitud_rechazada",
            "data": {
                "solicitud_id": solicitud_id,
                "id_taller": id_taller,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Enviar al cliente
        await self.connection_manager.send_to_user(user_id_cliente, event)
        
        logger.info(f"Evento emitido: solicitud_rechazada para solicitud {solicitud_id}")
    
    async def emit_tecnico_ubicacion_actualizada(
        self,
        servicio_id: int,
        empleado_id: int,
        latitud: float,
        longitud: float,
        timestamp: Optional[datetime] = None
    ):
        """Emite evento cuando se actualiza la ubicación de un técnico"""
        event = {
            "type": "tecnico_ubicacion_actualizada",
            "data": {
                "servicio_id": servicio_id,
                "empleado_id": empleado_id,
                "latitud": latitud,
                "longitud": longitud,
                "timestamp": (timestamp or datetime.utcnow()).isoformat()
            }
        }
        
        # Enviar a la sala del servicio
        await self.connection_manager.send_to_service_room(servicio_id, event)
        
        logger.info(f"Evento emitido: tecnico_ubicacion_actualizada para técnico {empleado_id}")
    
    async def emit_servicio_finalizado(
        self,
        servicio_id: int,
        user_id_cliente: int
    ):
        """Emite evento cuando un servicio se finaliza"""
        event = {
            "type": "servicio_finalizado",
            "data": {
                "servicio_id": servicio_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Enviar al cliente
        await self.connection_manager.send_to_user(user_id_cliente, event)
        
        # Enviar a la sala del servicio
        await self.connection_manager.send_to_service_room(servicio_id, event)
        
        logger.info(f"Evento emitido: servicio_finalizado para servicio {servicio_id}")
    
    async def emit_solicitud_creada(
        self,
        solicitud_id: int,
        id_taller: int,
        id_diagnostico: int,
        distancia_km: Optional[float] = None
    ):
        """Emite evento cuando se crea una nueva solicitud de servicio"""
        event = {
            "type": "solicitud_creada",
            "data": {
                "solicitud_id": solicitud_id,
                "id_taller": id_taller,
                "id_diagnostico": id_diagnostico,
                "distancia_km": distancia_km,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Enviar a todos los usuarios del taller
        # Necesitamos obtener los user_ids de los usuarios del taller
        # Por ahora, enviamos broadcast y el frontend filtrará
        await self.connection_manager.broadcast(event)
        
        logger.info(f"Evento emitido: solicitud_creada para solicitud {solicitud_id}, taller {id_taller}")


# Instancias globales
connection_manager = ConnectionManager()
event_emitter = WebSocketEventEmitter(connection_manager)


def get_connection_manager() -> ConnectionManager:
    """Retorna el gestor de conexiones"""
    return connection_manager


def get_event_emitter() -> WebSocketEventEmitter:
    """Retorna el emisor de eventos"""
    return event_emitter
