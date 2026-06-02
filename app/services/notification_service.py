"""
Servicio para envío de notificaciones push usando Firebase Cloud Messaging (FCM) API v1
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import json
import asyncio
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from app.models.dispositivo_usuario import DispositivoUsuario
from app.models.persona import Persona
from app.models.servicio import Servicio
from app.models.solicitud_servicio import SolicitudServicio
from app.models.solicitud_diagnostico import SolicitudDiagnostico
from app.models.diagnostico import Diagnostico
from app.models.taller import Taller
from app.models.rol_usuario import RolUsuario
from app.models.usuario import Usuario
from app.crud import crud_dispositivo_usuario
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# CLASE PARA LOGGING ESTRUCTURADO DE NOTIFICACIONES
# ============================================================================

class NotificationLogger:
    """
    Logger estructurado para notificaciones push.
    Registra eventos de notificaciones con campos JSON estructurados.
    """
    
    def __init__(self, logger_instance: logging.Logger):
        """
        Inicializa el logger de notificaciones.
        
        Args:
            logger_instance: Instancia del logger de Python
        """
        self.logger = logger_instance
    
    def log_notification_sent(
        self,
        tipo_notificacion: str,
        destinatario_id: int,
        num_tokens: int,
        titulo: str,
        success: bool = True
    ):
        """
        Registra el envío exitoso de una notificación.
        
        Args:
            tipo_notificacion: Tipo de notificación (ej: "nueva_solicitud", "tecnico_asignado")
            destinatario_id: ID de la persona o taller destinatario
            num_tokens: Número de tokens a los que se envió
            titulo: Título de la notificación
            success: Si el envío fue exitoso
        """
        extra_fields = {
            "event": "notification_sent",
            "notification_type": tipo_notificacion,
            "recipient_id": destinatario_id,
            "num_tokens": num_tokens,
            "title": titulo,
            "success": success
        }
        
        if success:
            self.logger.info(
                f"📤 Notificación enviada: {tipo_notificacion} a {num_tokens} dispositivo(s)",
                extra=extra_fields
            )
        else:
            self.logger.warning(
                f"⚠️ Notificación falló: {tipo_notificacion} a {num_tokens} dispositivo(s)",
                extra=extra_fields
            )
    
    def log_notification_failed(
        self,
        tipo_notificacion: str,
        destinatario_id: int,
        error: str,
        num_tokens: int = 0
    ):
        """
        Registra el fallo en el envío de una notificación.
        
        Args:
            tipo_notificacion: Tipo de notificación
            destinatario_id: ID del destinatario
            error: Mensaje de error
            num_tokens: Número de tokens involucrados
        """
        extra_fields = {
            "event": "notification_failed",
            "notification_type": tipo_notificacion,
            "recipient_id": destinatario_id,
            "error": error,
            "num_tokens": num_tokens
        }
        
        self.logger.error(
            f"❌ Error enviando notificación {tipo_notificacion}: {error}",
            extra=extra_fields
        )
    
    def log_token_registered(
        self,
        persona_id: int,
        token: str,
        plataforma: str = "unknown"
    ):
        """
        Registra el registro de un nuevo token FCM.
        
        Args:
            persona_id: ID de la persona
            token: Token FCM (se registra solo los primeros 20 caracteres)
            plataforma: Plataforma del dispositivo (android, ios, web)
        """
        extra_fields = {
            "event": "token_registered",
            "persona_id": persona_id,
            "token_prefix": token[:20] if token else "none",
            "platform": plataforma
        }
        
        self.logger.info(
            f"📱 Token registrado para persona {persona_id} ({plataforma})",
            extra=extra_fields
        )
    
    def log_token_removed(
        self,
        persona_id: int,
        token: str,
        reason: str = "manual"
    ):
        """
        Registra la eliminación de un token FCM.
        
        Args:
            persona_id: ID de la persona
            token: Token FCM eliminado
            reason: Razón de la eliminación (manual, invalid, inactive)
        """
        extra_fields = {
            "event": "token_removed",
            "persona_id": persona_id,
            "token_prefix": token[:20] if token else "none",
            "reason": reason
        }
        
        self.logger.info(
            f"🗑️ Token eliminado para persona {persona_id} (razón: {reason})",
            extra=extra_fields
        )
    
    def log_batch_cleanup(
        self,
        num_tokens_removed: int,
        reason: str = "inactive"
    ):
        """
        Registra la limpieza masiva de tokens.
        
        Args:
            num_tokens_removed: Número de tokens eliminados
            reason: Razón de la limpieza
        """
        extra_fields = {
            "event": "batch_cleanup",
            "num_tokens_removed": num_tokens_removed,
            "reason": reason
        }
        
        self.logger.info(
            f"🧹 Limpieza de tokens: {num_tokens_removed} tokens eliminados ({reason})",
            extra=extra_fields
        )


# ============================================================================
# CLASE PARA MANEJO DE ERRORES DE FCM
# ============================================================================

class FCMErrorHandler:
    """
    Manejador de errores de Firebase Cloud Messaging.
    Clasifica y maneja diferentes tipos de errores de FCM.
    """
    
    @staticmethod
    def handle_fcm_error(status_code: int, response_text: str, token: str) -> Dict[str, Any]:
        """
        Maneja errores de FCM según el código de estado HTTP.
        
        Args:
            status_code: Código de estado HTTP de la respuesta
            response_text: Texto de la respuesta de error
            token: Token FCM que causó el error
            
        Returns:
            Diccionario con información del error:
            - should_retry: Si se debe reintentar el envío
            - should_delete_token: Si se debe eliminar el token
            - error_type: Tipo de error
            - error_message: Mensaje descriptivo del error
        """
        # Token inválido o no registrado (eliminar token)
        if status_code == 404:
            return {
                "should_retry": False,
                "should_delete_token": True,
                "error_type": "INVALID_TOKEN",
                "error_message": f"Token no registrado o inválido: {token[:20]}..."
            }
        
        # Solicitud mal formada (eliminar token)
        if status_code == 400:
            return {
                "should_retry": False,
                "should_delete_token": True,
                "error_type": "BAD_REQUEST",
                "error_message": f"Token mal formado o inválido: {token[:20]}..."
            }
        
        # Error de autenticación (no reintentar, problema de configuración)
        if status_code == 401:
            return {
                "should_retry": False,
                "should_delete_token": False,
                "error_type": "AUTH_ERROR",
                "error_message": "Error de autenticación con FCM. Verificar credenciales."
            }
        
        # Rate limit excedido (reintentar con backoff)
        if status_code == 429:
            return {
                "should_retry": True,
                "should_delete_token": False,
                "error_type": "RATE_LIMIT",
                "error_message": "Límite de tasa excedido. Reintentando..."
            }
        
        # Errores del servidor de FCM (reintentar)
        if 500 <= status_code < 600:
            return {
                "should_retry": True,
                "should_delete_token": False,
                "error_type": "SERVER_ERROR",
                "error_message": f"Error del servidor FCM ({status_code}). Reintentando..."
            }
        
        # Error desconocido
        return {
            "should_retry": False,
            "should_delete_token": False,
            "error_type": "UNKNOWN_ERROR",
            "error_message": f"Error desconocido ({status_code}): {response_text[:100]}"
        }


class NotificationService:
    """Servicio para gestionar notificaciones push usando FCM API v1"""
    
    def __init__(self):
        # Configuración FCM v1
        self.fcm_credentials_path = getattr(settings, 'FCM_CREDENTIALS_PATH', None)
        self.project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None)
        self.fcm_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        self._access_token = None
        # Instanciar el manejador de errores
        self.error_handler = FCMErrorHandler()
        # Instanciar el logger estructurado
        self.notification_logger = NotificationLogger(logger)
    
    # ============================================================================
    # MÉTODOS DE RETRY CON EXPONENTIAL BACKOFF
    # ============================================================================
    
    async def enviar_notificacion_con_reintentos(
        self,
        token: str,
        titulo: str,
        mensaje: str,
        datos_extra: Optional[Dict[str, Any]] = None,
        max_intentos: int = 3
    ) -> Dict[str, Any]:
        """
        Envía una notificación con lógica de reintentos y exponential backoff.
        
        Args:
            token: Token FCM del dispositivo
            titulo: Título de la notificación
            mensaje: Cuerpo del mensaje
            datos_extra: Datos adicionales (opcional)
            max_intentos: Número máximo de intentos (default: 3)
            
        Returns:
            Diccionario con resultado:
            - success: True si se envió exitosamente
            - should_delete_token: True si el token debe eliminarse
            - attempts: Número de intentos realizados
            - error: Mensaje de error (si falló)
        """
        # Obtener access token
        access_token = self._get_access_token()
        if not access_token:
            return {
                "success": False,
                "should_delete_token": False,
                "attempts": 0,
                "error": "No se pudo obtener access token"
            }
        
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
                },
                "webpush": {
                    "headers": {
                        "Urgency": "high"
                    }
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Intentar enviar con reintentos
        for intento in range(1, max_intentos + 1):
            try:
                # Llamar a FCM API
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        self.fcm_url,
                        json=payload,
                        headers=headers
                    )
                    
                    # Éxito
                    if response.status_code == 200:
                        logger.info(f"✅ Notificación enviada exitosamente (intento {intento}/{max_intentos})")
                        return {
                            "success": True,
                            "should_delete_token": False,
                            "attempts": intento,
                            "error": None
                        }
                    
                    # Manejar error con el error handler
                    error_info = self.error_handler.handle_fcm_error(
                        response.status_code,
                        response.text,
                        token
                    )
                    
                    # Si no se debe reintentar, retornar inmediatamente
                    if not error_info["should_retry"]:
                        logger.warning(f"❌ {error_info['error_message']} (no se reintentará)")
                        return {
                            "success": False,
                            "should_delete_token": error_info["should_delete_token"],
                            "attempts": intento,
                            "error": error_info["error_message"]
                        }
                    
                    # Si se debe reintentar y no es el último intento, esperar con backoff
                    if intento < max_intentos:
                        # Exponential backoff: 1s, 2s, 4s
                        delay = 2 ** (intento - 1)
                        logger.info(f"⏳ Reintentando en {delay} segundos... (intento {intento}/{max_intentos})")
                        await asyncio.sleep(delay)
                    else:
                        # Último intento fallido
                        logger.error(f"❌ Falló después de {max_intentos} intentos: {error_info['error_message']}")
                        return {
                            "success": False,
                            "should_delete_token": error_info["should_delete_token"],
                            "attempts": intento,
                            "error": error_info["error_message"]
                        }
                        
            except asyncio.TimeoutError:
                # Timeout - reintentar si no es el último intento
                if intento < max_intentos:
                    delay = 2 ** (intento - 1)
                    logger.warning(f"⏱️ Timeout en intento {intento}/{max_intentos}. Reintentando en {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Timeout después de {max_intentos} intentos")
                    return {
                        "success": False,
                        "should_delete_token": False,
                        "attempts": intento,
                        "error": "Timeout después de múltiples intentos"
                    }
                    
            except Exception as e:
                # Error inesperado
                logger.error(f"💥 Error inesperado en intento {intento}/{max_intentos}: {e}")
                if intento < max_intentos:
                    delay = 2 ** (intento - 1)
                    await asyncio.sleep(delay)
                else:
                    return {
                        "success": False,
                        "should_delete_token": False,
                        "attempts": intento,
                        "error": str(e)
                    }
        
        # No debería llegar aquí, pero por seguridad
        return {
            "success": False,
            "should_delete_token": False,
            "attempts": max_intentos,
            "error": "Error desconocido"
        }
    
    # ============================================================================
    # MÉTODO CON DEGRADACIÓN GRACIOSA (GRACEFUL DEGRADATION)
    # ============================================================================
    
    async def notificar_con_fallback(
        self,
        db: AsyncSession,
        id_persona: int,
        titulo: str,
        mensaje: str,
        datos_extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envía notificación con degradación graciosa.
        Captura todas las excepciones y registra fallos sin propagarlos.
        
        Args:
            db: Sesión de base de datos
            id_persona: ID de la persona a notificar
            titulo: Título de la notificación
            mensaje: Cuerpo del mensaje
            datos_extra: Datos adicionales (opcional)
            
        Returns:
            True si se envió exitosamente, False si falló (sin lanzar excepciones)
        """
        try:
            # Obtener tokens de la persona
            tokens = await self.obtener_tokens_persona(db, id_persona)
            
            if not tokens:
                logger.info(f"Persona {id_persona} no tiene tokens FCM registrados")
                return True  # No es un error, simplemente no hay dispositivos
            
            # Intentar enviar notificación
            success = await self.enviar_notificacion_push_con_limpieza(
                tokens=tokens,
                titulo=titulo,
                mensaje=mensaje,
                datos_extra=datos_extra,
                db=db
            )
            
            if success:
                logger.info(f"✅ Notificación enviada exitosamente a persona {id_persona}")
            else:
                logger.warning(f"⚠️ No se pudo enviar notificación a persona {id_persona}")
            
            return success
            
        except Exception as e:
            # Capturar cualquier excepción y registrarla sin propagarla
            logger.error(f"💥 Error enviando notificación a persona {id_persona}: {e}", exc_info=True)
            return False
    
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
    
    # ============================================================================
    # NUEVOS MÉTODOS PARA NOTIFICACIONES A TALLERES
    # ============================================================================
    
    async def obtener_tokens_usuarios_taller(
        self,
        db: AsyncSession,
        id_taller: int
    ) -> List[str]:
        """
        Obtiene todos los tokens FCM de los usuarios asociados a un taller.
        
        Args:
            db: Sesión de base de datos
            id_taller: ID del taller
            
        Returns:
            Lista de tokens FCM de todos los usuarios del taller
        """
        try:
            # Buscar todos los usuarios que tienen roles en este taller
            result = await db.execute(
                select(Usuario, Persona).join(
                    Persona, Usuario.id_persona == Persona.id
                ).join(
                    RolUsuario, Usuario.id == RolUsuario.id_usuario
                ).where(
                    RolUsuario.id_taller == id_taller
                ).distinct()  # Evitar duplicados si un usuario tiene múltiples roles
            )
            
            usuarios_personas = result.all()
            
            if not usuarios_personas:
                logger.info(f"No se encontraron usuarios para el taller {id_taller}")
                return []
            
            # Obtener tokens de todos los usuarios del taller
            all_tokens = []
            for usuario, persona in usuarios_personas:
                # Obtener tokens FCM de cada persona
                tokens = await self.obtener_tokens_persona(db, persona.id)
                all_tokens.extend(tokens)
            
            logger.info(f"Se encontraron {len(all_tokens)} tokens para el taller {id_taller}")
            return all_tokens
            
        except Exception as e:
            logger.error(f"Error obteniendo tokens de usuarios del taller {id_taller}: {e}")
            return []
    
    async def notificar_nueva_solicitud_taller(
        self,
        db: AsyncSession,
        solicitud: SolicitudServicio,
        id_taller: int
    ) -> bool:
        """
        Notifica a todos los usuarios del taller cuando llega una nueva solicitud de servicio.
        
        Args:
            db: Sesión de base de datos
            solicitud: La solicitud de servicio creada
            id_taller: ID del taller que recibe la solicitud
            
        Returns:
            True si al menos una notificación fue enviada exitosamente
        """
        try:
            # Obtener información del diagnóstico y cliente
            result = await db.execute(
                select(Diagnostico, SolicitudDiagnostico, Persona).join(
                    SolicitudDiagnostico, Diagnostico.id_solicitud_diagnostico == SolicitudDiagnostico.id
                ).join(
                    Persona, SolicitudDiagnostico.id_persona == Persona.id
                ).where(
                    Diagnostico.id == solicitud.id_diagnostico
                )
            )
            
            row = result.first()
            if not row:
                logger.warning(f"No se encontró información del diagnóstico para solicitud {solicitud.id}")
                return False
            
            diagnostico, solicitud_diag, persona = row
            
            # Obtener tokens de todos los usuarios del taller
            tokens = await self.obtener_tokens_usuarios_taller(db, id_taller)
            
            if not tokens:
                logger.info(f"Taller {id_taller} no tiene usuarios con tokens FCM registrados")
                return True  # No es un error, simplemente no hay dispositivos
            
            # Preparar notificación
            titulo = "🚗 Nueva Solicitud de Servicio"
            mensaje = f"Nueva solicitud de {persona.nombre or 'un cliente'}. Ubicación: {solicitud_diag.ubicacion or 'No especificada'}"
            
            # Datos adicionales para la notificación
            datos_extra = {
                "tipo": "nueva_solicitud",
                "solicitud_id": str(solicitud.id),
                "diagnostico_id": str(diagnostico.id),
                "cliente_nombre": persona.nombre or "Cliente",
                "accion": "abrir_solicitud_detalle"
            }
            
            # Enviar notificación a todos los usuarios del taller
            return await self.enviar_notificacion_push(tokens, titulo, mensaje, datos_extra)
            
        except Exception as e:
            logger.error(f"Error notificando nueva solicitud al taller {id_taller}: {e}")
            return False
    
    async def notificar_solicitud_cancelada_taller(
        self,
        db: AsyncSession,
        solicitud: SolicitudServicio,
        id_taller: int,
        motivo_cancelacion: str = "Sin motivo especificado"
    ) -> bool:
        """
        Notifica a todos los usuarios del taller cuando un cliente cancela una solicitud.
        
        Args:
            db: Sesión de base de datos
            solicitud: La solicitud de servicio cancelada
            id_taller: ID del taller
            motivo_cancelacion: Razón de la cancelación
            
        Returns:
            True si al menos una notificación fue enviada exitosamente
        """
        try:
            # Obtener información del cliente
            result = await db.execute(
                select(Diagnostico, SolicitudDiagnostico, Persona).join(
                    SolicitudDiagnostico, Diagnostico.id_solicitud_diagnostico == SolicitudDiagnostico.id
                ).join(
                    Persona, SolicitudDiagnostico.id_persona == Persona.id
                ).where(
                    Diagnostico.id == solicitud.id_diagnostico
                )
            )
            
            row = result.first()
            if not row:
                logger.warning(f"No se encontró información para solicitud cancelada {solicitud.id}")
                return False
            
            diagnostico, solicitud_diag, persona = row
            
            # Obtener tokens de todos los usuarios del taller
            tokens = await self.obtener_tokens_usuarios_taller(db, id_taller)
            
            if not tokens:
                logger.info(f"Taller {id_taller} no tiene usuarios con tokens FCM registrados")
                return True
            
            # Preparar notificación
            titulo = "❌ Solicitud Cancelada"
            mensaje = f"{persona.nombre or 'Un cliente'} ha cancelado su solicitud. Motivo: {motivo_cancelacion}"
            
            # Datos adicionales
            datos_extra = {
                "tipo": "solicitud_cancelada",
                "solicitud_id": str(solicitud.id),
                "motivo": motivo_cancelacion,
                "accion": "abrir_solicitudes_lista"
            }
            
            # Enviar notificación
            return await self.enviar_notificacion_push(tokens, titulo, mensaje, datos_extra)
            
        except Exception as e:
            logger.error(f"Error notificando cancelación al taller {id_taller}: {e}")
            return False
    
    async def notificar_diagnostico_completado_taller(
        self,
        db: AsyncSession,
        diagnostico: Diagnostico,
        id_taller: int
    ) -> bool:
        """
        Notifica a todos los usuarios del taller cuando un diagnóstico es completado.
        
        Args:
            db: Sesión de base de datos
            diagnostico: El diagnóstico completado
            id_taller: ID del taller
            
        Returns:
            True si al menos una notificación fue enviada exitosamente
        """
        try:
            # Obtener información del técnico que completó el diagnóstico
            result = await db.execute(
                select(Persona).where(
                    Persona.id == diagnostico.id_persona_tecnico
                )
            )
            
            tecnico = result.scalar_one_or_none()
            tecnico_nombre = tecnico.nombre if tecnico else "Un técnico"
            
            # Obtener tokens de todos los usuarios del taller
            tokens = await self.obtener_tokens_usuarios_taller(db, id_taller)
            
            if not tokens:
                logger.info(f"Taller {id_taller} no tiene usuarios con tokens FCM registrados")
                return True
            
            # Preparar notificación
            titulo = "✅ Diagnóstico Completado"
            mensaje = f"{tecnico_nombre} ha completado un diagnóstico. Revisa los detalles y aprueba el servicio."
            
            # Datos adicionales
            datos_extra = {
                "tipo": "diagnostico_completado",
                "diagnostico_id": str(diagnostico.id),
                "tecnico_nombre": tecnico_nombre,
                "accion": "abrir_diagnostico_detalle"
            }
            
            # Enviar notificación
            return await self.enviar_notificacion_push(tokens, titulo, mensaje, datos_extra)
            
        except Exception as e:
            logger.error(f"Error notificando diagnóstico completado al taller {id_taller}: {e}")
            return False
    
    # ============================================================================
    # NUEVOS MÉTODOS PARA NOTIFICACIONES A CLIENTES
    # ============================================================================
    
    async def notificar_tecnico_asignado(
        self,
        db: AsyncSession,
        servicio: Servicio,
        tecnico: Persona
    ) -> bool:
        """
        Notifica al cliente cuando un técnico es asignado a su servicio.
        
        Args:
            db: Sesión de base de datos
            servicio: El servicio con técnico asignado
            tecnico: La persona (técnico) asignada
            
        Returns:
            True si la notificación fue enviada exitosamente
        """
        try:
            # Obtener información del cliente
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
            
            # Preparar notificación
            titulo = "👨‍🔧 Técnico Asignado"
            mensaje = f"{tecnico.nombre or 'Un técnico'} ha sido asignado a tu servicio. Pronto estará en camino."
            
            # Datos adicionales
            datos_extra = {
                "tipo": "tecnico_asignado",
                "servicio_id": str(servicio.id),
                "tecnico_id": str(tecnico.id),
                "tecnico_nombre": tecnico.nombre or "Técnico",
                "tecnico_telefono": tecnico.telefono or "",
                "accion": "abrir_servicio_detalle"
            }
            
            # Enviar notificación
            return await self.enviar_notificacion_push(tokens, titulo, mensaje, datos_extra)
            
        except Exception as e:
            logger.error(f"Error notificando técnico asignado: {e}")
            return False
    
    # ============================================================================
    # MÉTODOS DE GESTIÓN DEL CICLO DE VIDA DE TOKENS
    # ============================================================================
    
    async def limpiar_tokens_inactivos(
        self,
        db: AsyncSession,
        dias_inactividad: int = 90
    ) -> int:
        """
        Elimina tokens FCM que han estado inactivos por más de X días.
        
        Args:
            db: Sesión de base de datos
            dias_inactividad: Número de días de inactividad antes de eliminar (default: 90)
            
        Returns:
            Número de tokens eliminados
        """
        try:
            from datetime import datetime, timedelta
            
            # Calcular fecha límite
            fecha_limite = datetime.utcnow() - timedelta(days=dias_inactividad)
            
            # Buscar tokens inactivos
            # NOTA: Este método requiere que la tabla tenga la columna fecha_ultima_actividad
            # Si no existe, este método no funcionará hasta que se ejecute la migración
            result = await db.execute(
                select(DispositivoUsuario).where(
                    DispositivoUsuario.fecha_ultima_actividad < fecha_limite
                )
            )
            
            tokens_inactivos = result.scalars().all()
            count = len(tokens_inactivos)
            
            if count == 0:
                logger.info("No se encontraron tokens inactivos para eliminar")
                return 0
            
            # Eliminar tokens inactivos
            for dispositivo in tokens_inactivos:
                await db.delete(dispositivo)
            
            await db.commit()
            logger.info(f"✅ Se eliminaron {count} tokens inactivos (más de {dias_inactividad} días)")
            
            return count
            
        except Exception as e:
            logger.error(f"Error limpiando tokens inactivos: {e}")
            await db.rollback()
            return 0
    
    async def validar_y_limpiar_token(
        self,
        db: AsyncSession,
        token: str
    ) -> bool:
        """
        Valida un token con FCM y lo elimina si es inválido.
        
        Args:
            db: Sesión de base de datos
            token: Token FCM a validar
            
        Returns:
            True si el token es válido, False si fue eliminado
        """
        try:
            # Obtener access token de FCM
            access_token = self._get_access_token()
            if not access_token:
                logger.warning("No se pudo obtener access token para validar token")
                return True  # Asumir válido si no podemos validar
            
            # Intentar enviar una notificación de prueba (sin contenido visible)
            payload = {
                "message": {
                    "token": token,
                    "data": {
                        "tipo": "validacion",
                        "timestamp": str(int(__import__('time').time()))
                    }
                }
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Enviar solicitud a FCM
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers
                )
                
                # Si el token es inválido (404 o 400), eliminarlo
                if response.status_code in [404, 400]:
                    logger.warning(f"Token inválido detectado, eliminando: {token[:20]}...")
                    
                    # Buscar y eliminar el token de la base de datos
                    result = await db.execute(
                        select(DispositivoUsuario).where(
                            DispositivoUsuario.token_fcm == token
                        )
                    )
                    dispositivo = result.scalar_one_or_none()
                    
                    if dispositivo:
                        await db.delete(dispositivo)
                        await db.commit()
                        logger.info(f"✅ Token inválido eliminado de la base de datos")
                    
                    return False
                
                # Token válido
                return True
                
        except Exception as e:
            logger.error(f"Error validando token: {e}")
            return True  # Asumir válido en caso de error
    
    async def enviar_notificacion_push_con_limpieza(
        self,
        tokens: List[str],
        titulo: str,
        mensaje: str,
        datos_extra: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Envía notificación push y automáticamente limpia tokens inválidos.
        Esta es una versión mejorada de enviar_notificacion_push que maneja tokens inválidos.
        
        Args:
            tokens: Lista de tokens FCM
            titulo: Título de la notificación
            mensaje: Cuerpo del mensaje
            datos_extra: Datos adicionales (opcional)
            db: Sesión de base de datos (opcional, para limpiar tokens inválidos)
            
        Returns:
            True si al menos una notificación fue enviada exitosamente
        """
        if not self.fcm_credentials_path or not self.project_id:
            logger.warning("FCM no configurado correctamente")
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
        tokens_invalidos = []
        
        # Enviar notificación a cada token
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
                        },
                        "webpush": {
                            "headers": {
                                "Urgency": "high"
                            }
                        }
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                # Llamar a FCM API
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        self.fcm_url,
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        success_count += 1
                        logger.info(f"✅ Notificación enviada a token: {token[:20]}...")
                    elif response.status_code in [404, 400]:
                        # Token inválido - marcar para eliminación
                        failure_count += 1
                        tokens_invalidos.append(token)
                        logger.warning(f"❌ Token inválido: {token[:20]}... (será eliminado)")
                    else:
                        failure_count += 1
                        logger.error(f"❌ Error FCM {response.status_code} para token {token[:20]}...")
                        
            except Exception as e:
                failure_count += 1
                logger.error(f"💥 Error enviando notificación a token {token[:20]}...: {e}")
        
        # Limpiar tokens inválidos de la base de datos
        if tokens_invalidos and db:
            try:
                for token in tokens_invalidos:
                    result = await db.execute(
                        select(DispositivoUsuario).where(
                            DispositivoUsuario.token_fcm == token
                        )
                    )
                    dispositivo = result.scalar_one_or_none()
                    if dispositivo:
                        await db.delete(dispositivo)
                
                await db.commit()
                logger.info(f"🧹 Se eliminaron {len(tokens_invalidos)} tokens inválidos de la base de datos")
            except Exception as e:
                logger.error(f"Error limpiando tokens inválidos: {e}")
                await db.rollback()
        
        logger.info(f"📊 Resumen: {success_count} éxitos, {failure_count} fallos, {len(tokens_invalidos)} tokens eliminados")
        return success_count > 0

# Instancia global del servicio
notification_service = NotificationService()