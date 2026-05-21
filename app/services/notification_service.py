"""
Servicio para envío de notificaciones push usando Firebase Cloud Messaging (FCM) API v1
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from app.models.dispositivo_usuario import DispositivoUsuario
from app.models.persona import Persona
from app.models.servicio import Servicio
from app.models.solicitud_servicio import SolicitudServicio
from app.models.solicitud_diagnostico import SolicitudDiagnostico
from app.models.diagnostico import Diagnostico
from app.crud import crud_dispositivo_usuario
from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Servicio para gestionar notificaciones push usando FCM API v1"""
    
    def __init__(self):
        # Configuración FCM v1
        self.fcm_credentials_path = getattr(settings, 'FCM_CREDENTIALS_PATH', None)
        self.project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None)
        self.fcm_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        self._access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        """
        Obtiene el access token de OAuth2 usando las credenciales de servicio
        """
        try:
            if not self.fcm_credentials_path:
                logger.warning("FCM_CREDENTIALS_PATH no configurado")
                return None
            
            # Si la ruta es relativa, buscar desde el directorio del proyecto
            import os
            if not os.path.isabs(self.fcm_credentials_path):
                # Obtener directorio base del proyecto
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                credentials_path = os.path.join(base_dir, self.fcm_credentials_path)
            else:
                credentials_path = self.fcm_credentials_path
            
            logger.info(f"Cargando credenciales FCM desde: {credentials_path}")
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            
            credentials.refresh(Request())
            logger.info("✅ Access token obtenido exitosamente")
            return credentials.token
            
        except Exception as e:
            logger.error(f"Error obteniendo access token: {e}")
            return None
    
    async def enviar_notificacion_push(
        self,
        tokens: List[str],
        titulo: str,
        mensaje: str,
        datos_extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envía notificación push a una lista de tokens FCM usando API v1
        """
        if not self.fcm_credentials_path or not self.project_id:
            logger.warning("FCM no configurado correctamente (falta credentials o project_id)")
            return False
        
        if not tokens:
            logger.info("No hay tokens FCM para enviar notificación")
            return True
        
        # Obtener access token
        access_token = self._get_access_token()
        if not access_token:
            logger.error("No se pudo obtener access token de FCM")
            return False
        
        success_count = 0
        failure_count = 0
        
        # FCM v1 requiere enviar un mensaje por token
        for token in tokens:
            try:
                # Preparar payload FCM v1
                payload = {
                    "message": {
                        "token": token,
                        "notification": {
                            "title": titulo,
                            "body": mensaje
                        },
                        "data": {str(k): str(v) for k, v in (datos_extra or {}).items()},
                        "android": {
                            "priority": "high",
                            "notification": {
                                "sound": "default",
                                "channel_id": "default"
                            }
                        }
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        self.fcm_url,
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        success_count += 1
                        logger.info(f"Notificación enviada exitosamente a token: {token[:20]}...")
                    else:
                        failure_count += 1
                        logger.error(f"Error FCM para token {token[:20]}...: {response.status_code} - {response.text}")
                        
            except Exception as e:
                failure_count += 1
                logger.error(f"Error enviando notificación a token {token[:20]}...: {e}")
        
        logger.info(f"Notificaciones enviadas: {success_count} éxitos, {failure_count} fallos")
        return success_count > 0
    
    async def obtener_tokens_persona(self, db: AsyncSession, id_persona: int) -> List[str]:
        """
        Obtiene todos los tokens FCM de una persona
        """
        dispositivos = await crud_dispositivo_usuario.dispositivo_usuario.get_by_persona(db, id_persona)
        return [d.token_fcm for d in dispositivos if d.token_fcm]
    
    async def notificar_solicitud_aceptada(
        self,
        db: AsyncSession,
        servicio: Servicio
    ) -> bool:
        """
        Notifica al cliente que su solicitud fue aceptada
        """
        try:
            # Obtener datos del cliente
            result = await db.execute(
                select(SolicitudDiagnostico, Persona).join(
                    Diagnostico, SolicitudDiagnostico.id == Diagnostico.id_solicitud_diagnostico
                ).join(
                    SolicitudServicio, Diagnostico.id == SolicitudServicio.id_diagnostico
                ).join(
                    Persona, SolicitudDiagnostico.id_persona == Persona.id
                ).where(
                    SolicitudServicio.id == servicio.id_solicitud_servicio
                )
            )
            
            row = result.first()
            if not row:
                logger.warning(f"No se encontró cliente para servicio {servicio.id}")
                return False
            
            solicitud_diag, persona = row
            
            # Obtener tokens FCM del cliente
            tokens = await self.obtener_tokens_persona(db, persona.id)
            
            if not tokens:
                logger.info(f"Cliente {persona.id} no tiene tokens FCM registrados")
                return True
            
            # Enviar notificación
            titulo = "¡Solicitud Aceptada!"
            mensaje = f"Un taller ha aceptado tu solicitud de servicio. El técnico está en camino."
            
            datos_extra = {
                "tipo": "solicitud_aceptada",
                "servicio_id": str(servicio.id),
                "accion": "abrir_servicio_detalle"
            }
            
            return await self.enviar_notificacion_push(tokens, titulo, mensaje, datos_extra)
            
        except Exception as e:
            logger.error(f"Error notificando solicitud aceptada: {e}")
            return False
    
    async def notificar_cambio_estado_servicio(
        self,
        db: AsyncSession,
        servicio: Servicio,
        estado_anterior: str,
        estado_nuevo: str
    ) -> bool:
        """
        Notifica al cliente sobre cambios de estado del servicio
        """
        try:
            # Obtener datos del cliente
            result = await db.execute(
                select(SolicitudDiagnostico, Persona).join(
                    Diagnostico, SolicitudDiagnostico.id == Diagnostico.id_solicitud_diagnostico
                ).join(
                    SolicitudServicio, Diagnostico.id == SolicitudServicio.id_diagnostico
                ).join(
                    Persona, SolicitudDiagnostico.id_persona == Persona.id
                ).where(
                    SolicitudServicio.id == servicio.id_solicitud_servicio
                )
            )
            
            row = result.first()
            if not row:
                return False
            
            solicitud_diag, persona = row
            
            # Obtener tokens FCM del cliente
            tokens = await self.obtener_tokens_persona(db, persona.id)
            
            if not tokens:
                return True
            
            # Generar mensaje según el estado
            titulo, mensaje = self._generar_mensaje_estado(estado_nuevo)
            
            datos_extra = {
                "tipo": "cambio_estado_servicio",
                "servicio_id": str(servicio.id),
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "accion": "abrir_servicio_detalle"
            }
            
            return await self.enviar_notificacion_push(tokens, titulo, mensaje, datos_extra)
            
        except Exception as e:
            logger.error(f"Error notificando cambio de estado: {e}")
            return False
    
    async def notificar_servicio_finalizado(
        self,
        db: AsyncSession,
        servicio: Servicio
    ) -> bool:
        """
        Notifica al cliente que su servicio ha sido finalizado
        """
        try:
            # Obtener datos del cliente
            result = await db.execute(
                select(SolicitudDiagnostico, Persona).join(
                    Diagnostico, SolicitudDiagnostico.id == Diagnostico.id_solicitud_diagnostico
                ).join(
                    SolicitudServicio, Diagnostico.id == SolicitudServicio.id_diagnostico
                ).join(
                    Persona, SolicitudDiagnostico.id_persona == Persona.id
                ).where(
                    SolicitudServicio.id == servicio.id_solicitud_servicio
                )
            )
            
            row = result.first()
            if not row:
                return False
            
            solicitud_diag, persona = row
            
            # Obtener tokens FCM del cliente
            tokens = await self.obtener_tokens_persona(db, persona.id)
            
            if not tokens:
                return True
            
            # Enviar notificación
            titulo = "¡Servicio Completado!"
            mensaje = "Tu servicio ha sido finalizado exitosamente. ¡No olvides valorar tu experiencia!"
            
            datos_extra = {
                "tipo": "servicio_finalizado",
                "servicio_id": str(servicio.id),
                "accion": "abrir_valoracion"
            }
            
            return await self.enviar_notificacion_push(tokens, titulo, mensaje, datos_extra)
            
        except Exception as e:
            logger.error(f"Error notificando servicio finalizado: {e}")
            return False
    
    def _generar_mensaje_estado(self, estado: str) -> tuple[str, str]:
        """
        Genera título y mensaje según el estado del servicio
        """
        mensajes = {
            "tecnico_asignado": (
                "Técnico Asignado",
                "Se ha asignado un técnico a tu servicio"
            ),
            "en_camino": (
                "Técnico en Camino",
                "El técnico está en camino hacia tu ubicación"
            ),
            "en_lugar": (
                "Técnico en el Lugar",
                "El técnico ha llegado a tu ubicación"
            ),
            "en_atencion": (
                "Servicio en Atención",
                "El técnico está trabajando en tu vehículo"
            ),
            "finalizado": (
                "¡Servicio Completado!",
                "Tu servicio ha sido finalizado exitosamente"
            ),
            "cancelado": (
                "Servicio Cancelado",
                "Tu servicio ha sido cancelado"
            )
        }
        
        return mensajes.get(estado, ("Actualización de Servicio", f"Tu servicio cambió a: {estado}"))

# Instancia global del servicio
notification_service = NotificationService()