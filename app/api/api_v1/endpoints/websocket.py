"""
Endpoints de WebSocket para tiempo real
Permite conexiones WebSocket para actualizaciones en tiempo real
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from typing import Optional
import logging

from app.services.websocket_service import get_connection_manager
from app.core.deps import get_current_persona_from_token
from app.models.persona import Persona
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    servicio_id: Optional[int] = Query(None)
):
    """
    Endpoint WebSocket principal para conexiones en tiempo real
    
    **Parámetros:**
    - **token**: Token JWT de autenticación (requerido)
    - **servicio_id**: ID del servicio para unirse a la sala específica (opcional)
    
    **Eventos recibidos:**
    - `join_service`: {"servicio_id": int} - Unirse a sala de servicio
    - `leave_service`: {"servicio_id": int} - Salir de sala de servicio
    
    **Eventos enviados:**
    - `servicio_estado_cambiado`: Cuando cambia estado de servicio
    - `solicitud_aceptada`: Cuando taller acepta solicitud
    - `solicitud_rechazada`: Cuando taller rechaza solicitud
    - `tecnico_ubicacion_actualizada`: Cuando técnico actualiza ubicación
    - `servicio_finalizado`: Cuando servicio se completa
    """
    connection_manager = get_connection_manager()
    
    # Validar token
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("Conexión WebSocket rechazada: no token proporcionado")
        return
    
    try:
        # Obtener sesión de base de datos para autenticación
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            # Verificar token y obtener usuario
            persona = await get_current_persona_from_token(token, db)
            user_id = persona.id
        finally:
            # Cerrar el generador de BD
            try:
                await db_gen.__anext__()
            except StopAsyncIteration:
                pass
        
        # Aceptar conexión
        await websocket.accept()
        logger.info(f"WebSocket aceptado para usuario {user_id}")
        
        # Registrar conexión
        await connection_manager.connect(websocket, user_id)
        
        # Si se proporcionó servicio_id, unir a la sala
        if servicio_id:
            await connection_manager.join_service_room(user_id, servicio_id)
            await websocket.send_json({
                "type": "connected",
                "data": {
                    "user_id": user_id,
                    "servicio_id": servicio_id,
                    "message": "Conectado a sala de servicio"
                }
            })
        else:
            await websocket.send_json({
                "type": "connected",
                "data": {
                    "user_id": user_id,
                    "message": "Conectado a WebSocket general"
                }
            })
        
        # Escuchar mensajes del cliente
        try:
            while True:
                data = await websocket.receive_json()
                
                # Procesar mensajes del cliente
                message_type = data.get("type")
                message_data = data.get("data", {})
                
                if message_type == "join_service":
                    servicio_id_join = message_data.get("servicio_id")
                    if servicio_id_join:
                        await connection_manager.join_service_room(user_id, servicio_id_join)
                        await websocket.send_json({
                            "type": "joined_service",
                            "data": {
                                "servicio_id": servicio_id_join,
                                "message": f"Unido a sala de servicio {servicio_id_join}"
                            }
                        })
                
                elif message_type == "leave_service":
                    servicio_id_leave = message_data.get("servicio_id")
                    if servicio_id_leave:
                        await connection_manager.leave_service_room(user_id, servicio_id_leave)
                        await websocket.send_json({
                            "type": "left_service",
                            "data": {
                                "servicio_id": servicio_id_leave,
                                "message": f"Salió de sala de servicio {servicio_id_leave}"
                            }
                        })
                
                elif message_type == "ping":
                    # Respuesta a ping para keep-alive
                    await websocket.send_json({
                        "type": "pong",
                        "data": {"timestamp": message_data.get("timestamp")}
                    })
                
                else:
                    logger.warning(f"Tipo de mensaje desconocido: {message_type}")
                    await websocket.send_json({
                        "type": "error",
                        "data": {
                            "message": f"Tipo de mensaje desconocido: {message_type}"
                        }
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket desconectado para usuario {user_id}")
        
        except Exception as e:
            logger.error(f"Error en WebSocket para usuario {user_id}: {e}")
        
        finally:
            # Limpiar conexión - solo salir de sala si se proporcionó servicio_id inicial
            if servicio_id:
                await connection_manager.leave_service_room(user_id, servicio_id)
            await connection_manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"Error autenticando WebSocket: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)


@router.get("/health")
async def websocket_health():
    """
    Health check del módulo WebSocket
    """
    connection_manager = get_connection_manager()
    
    return {
        "status": "healthy",
        "module": "websocket",
        "active_connections": len(connection_manager.active_connections),
        "active_rooms": len(connection_manager.service_rooms),
        "message": "WebSocket module operational"
    }
