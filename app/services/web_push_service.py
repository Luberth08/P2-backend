"""
Servicio para envío de notificaciones Web Push usando pywebpush
"""
import logging
import json
import os
import base64
from typing import List, Optional, Dict, Any
from pywebpush import webpush, WebPushException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from app.models.dispositivo_usuario import DispositivoUsuario
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebPushService:
    """Servicio para gestionar notificaciones Web Push nativas"""
    
    def __init__(self):
        # Leer la clave privada desde el archivo PEM
        private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vapid_private_key.pem')
        
        self.vapid_private_key_path = None
        self.vapid_public_key = None
        
        try:
            if os.path.exists(private_key_path):
                # Guardar la ruta del archivo en lugar del contenido
                self.vapid_private_key_path = private_key_path
                
                # Cargar la clave para validarla y extraer la pública
                with open(private_key_path, 'r') as f:
                    private_pem = f.read()
                
                private_key_obj = serialization.load_pem_private_key(
                    private_pem.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                
                # Obtener la clave pública en formato base64url
                public_key_obj = private_key_obj.public_key()
                public_bytes = public_key_obj.public_bytes(
                    encoding=serialization.Encoding.X962,
                    format=serialization.PublicFormat.UncompressedPoint
                )
                vapid_public_key_extracted = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
                
                # Usar la clave pública del .env si existe, sino la extraída
                self.vapid_public_key = settings.FCM_VAPID_KEY or vapid_public_key_extracted
                
                logger.info("✅ Clave privada VAPID cargada desde archivo PEM")
                logger.info(f"📌 Clave pública VAPID: {self.vapid_public_key[:50]}...")
                
                # Advertir si la clave del .env no coincide
                if settings.FCM_VAPID_KEY and settings.FCM_VAPID_KEY != vapid_public_key_extracted:
                    logger.warning("⚠️ La clave FCM_VAPID_KEY del .env no coincide con la clave privada")
                    logger.warning(f"⚠️ Clave esperada: {vapid_public_key_extracted}")
                    
            else:
                logger.error(f"❌ Archivo no encontrado: {private_key_path}")
                self.vapid_private_key_path = None
                self.vapid_public_key = settings.FCM_VAPID_KEY
                
        except Exception as e:
            logger.error(f"❌ Error cargando clave privada VAPID: {e}")
            self.vapid_private_key_path = None
            self.vapid_public_key = settings.FCM_VAPID_KEY
        
        self.vapid_claims = {
            "sub": "mailto:luberthgutierrez@gmail.com"  # Email de contacto
        }
        
        # Validar que las claves VAPID estén configuradas
        if not self.vapid_private_key_path:
            logger.warning("⚠️ VAPID_PRIVATE_KEY no está configurada")
        if not self.vapid_public_key:
            logger.warning("⚠️ FCM_VAPID_KEY no está configurada en .env")
    
    async def enviar_notificacion_web_push(
        self,
        subscriptions: List[dict],
        titulo: str,
        mensaje: str,
        datos_extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envía notificación Web Push a una lista de suscripciones
        
        Args:
            subscriptions: Lista de suscripciones Web Push (JSON)
            titulo: Título de la notificación
            mensaje: Cuerpo del mensaje
            datos_extra: Datos adicionales (opcional)
            
        Returns:
            True si al menos una notificación fue enviada exitosamente
        """
        if not subscriptions:
            logger.info("No hay suscripciones Web Push para enviar notificación")
            return True
        
        # Validar que las claves VAPID estén configuradas
        if not self.vapid_private_key_path:
            logger.error("❌ No se puede enviar Web Push: VAPID_PRIVATE_KEY no configurada")
            return False
        
        if not self.vapid_public_key:
            logger.error("❌ No se puede enviar Web Push: FCM_VAPID_KEY no configurada")
            return False
        
        success_count = 0
        failure_count = 0
        
        # Preparar payload
        payload = {
            "notification": {
                "title": titulo,
                "body": mensaje,
                "icon": "/icon.png",
                "badge": "/badge.png",
                "data": datos_extra or {}
            }
        }
        
        payload_str = json.dumps(payload)
        
        for subscription in subscriptions:
            try:
                # Enviar usando pywebpush CON VAPID (usando ruta del archivo)
                webpush(
                    subscription_info=subscription,
                    data=payload_str,
                    vapid_private_key=self.vapid_private_key_path,
                    vapid_claims=self.vapid_claims
                )
                
                success_count += 1
                endpoint = subscription.get('endpoint', '')
                logger.info(f"✅ Notificación Web Push enviada a: {endpoint[:50]}...")
                
            except WebPushException as e:
                failure_count += 1
                logger.error(f"❌ Error Web Push: {e}")
                
                # Si el error es 404 o 410, la suscripción expiró
                if e.response and e.response.status_code in [404, 410]:
                    logger.warning(f"⚠️ Suscripción expirada: {subscription.get('endpoint', '')[:50]}...")
                    
            except Exception as e:
                failure_count += 1
                logger.error(f"💥 Error inesperado enviando Web Push: {e}")
        
        logger.info(f"📊 Notificaciones Web Push: {success_count} éxitos, {failure_count} fallos")
        return success_count > 0
    
    async def obtener_suscripciones_persona(
        self,
        db: AsyncSession,
        id_persona: int
    ) -> List[dict]:
        """
        Obtiene todas las suscripciones Web Push de una persona
        
        Args:
            db: Sesión de base de datos
            id_persona: ID de la persona
            
        Returns:
            Lista de suscripciones Web Push (JSON)
        """
        try:
            result = await db.execute(
                select(DispositivoUsuario).where(
                    DispositivoUsuario.id_persona == id_persona,
                    DispositivoUsuario.plataforma == "web"
                )
            )
            
            dispositivos = result.scalars().all()
            
            suscripciones = []
            for dispositivo in dispositivos:
                try:
                    # El token_fcm contiene el JSON de la suscripción Web Push
                    subscription_json = json.loads(dispositivo.token_fcm)
                    suscripciones.append(subscription_json)
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Token inválido en dispositivo {dispositivo.id}")
            
            return suscripciones
            
        except Exception as e:
            logger.error(f"Error obteniendo suscripciones Web Push: {e}")
            return []
    
    async def notificar_persona_web_push(
        self,
        db: AsyncSession,
        id_persona: int,
        titulo: str,
        mensaje: str,
        datos_extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Notifica a una persona usando Web Push
        
        Args:
            db: Sesión de base de datos
            id_persona: ID de la persona a notificar
            titulo: Título de la notificación
            mensaje: Cuerpo del mensaje
            datos_extra: Datos adicionales (opcional)
            
        Returns:
            True si se envió exitosamente
        """
        try:
            # Obtener suscripciones de la persona
            subscriptions = await self.obtener_suscripciones_persona(db, id_persona)
            
            if not subscriptions:
                logger.info(f"Persona {id_persona} no tiene suscripciones Web Push")
                return True
            
            # Enviar notificación
            return await self.enviar_notificacion_web_push(
                subscriptions, titulo, mensaje, datos_extra
            )
            
        except Exception as e:
            logger.error(f"Error notificando a persona {id_persona}: {e}")
            return False


# Instancia global
web_push_service = WebPushService()
