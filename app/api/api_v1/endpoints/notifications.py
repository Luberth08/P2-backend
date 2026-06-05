"""
Endpoints para gestión de notificaciones push
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from app.db.session import get_db
from app.core.deps import get_current_usuario
from app.models.usuario import Usuario
from app.crud import crud_dispositivo_usuario
from app.models.dispositivo_usuario import DispositivoUsuario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])

class TokenFCMRequest(BaseModel):
    token_fcm: str

class WebPushSubscriptionRequest(BaseModel):
    subscription: dict  # JSON de la suscripción push

class TokenFCMResponse(BaseModel):
    success: bool
    message: str

@router.post("/register-web-push", response_model=TokenFCMResponse)
async def registrar_web_push(
    request: WebPushSubscriptionRequest,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Registra una suscripción Web Push nativa (alternativa a FCM)
    """
    try:
        import json
        from sqlalchemy import select
        
        # Extraer el endpoint de la suscripción (lo usaremos como identificador único)
        subscription_json = request.subscription
        endpoint = subscription_json.get('endpoint')
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Endpoint de suscripción faltante"
            )
        
        # Guardar la suscripción completa como JSON en el campo token_fcm
        subscription_str = json.dumps(subscription_json)
        
        # Buscar si ya existe una suscripción con este endpoint
        # Buscar en el JSON almacenado (el endpoint está dentro del JSON)
        result = await db.execute(
            select(DispositivoUsuario).where(
                DispositivoUsuario.token_fcm.like(f'%{endpoint}%'),
                DispositivoUsuario.id_persona == current_usuario.id_persona
            )
        )
        dispositivo_existente = result.scalars().first()
        
        if dispositivo_existente:
            # Actualizar la suscripción
            dispositivo_existente.token_fcm = subscription_str
            dispositivo_existente.plataforma = "web"
            await db.commit()
            await db.refresh(dispositivo_existente)
            
            logger.info(f"✅ Suscripción Web Push actualizada para usuario {current_usuario.id}")
            return TokenFCMResponse(
                success=True,
                message="Suscripción Web Push actualizada"
            )
        
        # Crear nuevo registro
        nuevo_dispositivo = DispositivoUsuario(
            token_fcm=subscription_str,
            id_persona=current_usuario.id_persona,
            plataforma="web"
        )
        
        db.add(nuevo_dispositivo)
        await db.commit()
        await db.refresh(nuevo_dispositivo)
        
        logger.info(f"✅ Nueva suscripción Web Push registrada para usuario {current_usuario.id}")
        return TokenFCMResponse(
            success=True,
            message="Suscripción Web Push registrada exitosamente"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error registrando suscripción Web Push: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registrando suscripción Web Push: {str(e)}"
        )

@router.post("/unregister-web-push", response_model=TokenFCMResponse)
async def desregistrar_web_push(
    endpoint: str,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina una suscripción Web Push
    """
    try:
        dispositivo = await crud_dispositivo_usuario.dispositivo_usuario.get_by_token(
            db, endpoint
        )
        
        if dispositivo and dispositivo.id_persona == current_usuario.id_persona:
            await crud_dispositivo_usuario.dispositivo_usuario.delete(db, dispositivo.id)
            await db.commit()
            
            return TokenFCMResponse(
                success=True,
                message="Suscripción Web Push eliminada exitosamente"
            )
        
        return TokenFCMResponse(
            success=True,
            message="Suscripción Web Push no encontrada"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando suscripción Web Push: {str(e)}"
        )

@router.post("/register-token", response_model=TokenFCMResponse)
async def registrar_token_fcm(
    request: TokenFCMRequest,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Registra o actualiza el token FCM del dispositivo del usuario
    """
    try:
        # Verificar si ya existe un dispositivo con este token
        dispositivo_existente = await crud_dispositivo_usuario.dispositivo_usuario.get_by_token(
            db, request.token_fcm
        )
        
        if dispositivo_existente:
            # Si el token ya existe pero es de otra persona, actualizarlo
            if dispositivo_existente.id_persona != current_usuario.id_persona:
                dispositivo_existente.id_persona = current_usuario.id_persona
                await db.commit()
                await db.refresh(dispositivo_existente)
                
                return TokenFCMResponse(
                    success=True,
                    message="Token FCM actualizado para el usuario actual"
                )
            else:
                return TokenFCMResponse(
                    success=True,
                    message="Token FCM ya registrado para este usuario"
                )
        
        # Crear nuevo registro de dispositivo
        nuevo_dispositivo = DispositivoUsuario(
            token_fcm=request.token_fcm,
            id_persona=current_usuario.id_persona
        )
        
        db.add(nuevo_dispositivo)
        await db.commit()
        await db.refresh(nuevo_dispositivo)
        
        return TokenFCMResponse(
            success=True,
            message="Token FCM registrado exitosamente"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registrando token FCM: {str(e)}"
        )

@router.delete("/unregister-token", response_model=TokenFCMResponse)
async def desregistrar_token_fcm(
    request: TokenFCMRequest,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina el token FCM del dispositivo (cuando el usuario cierra sesión)
    """
    try:
        # Buscar y eliminar el dispositivo
        dispositivo = await crud_dispositivo_usuario.dispositivo_usuario.get_by_token(
            db, request.token_fcm
        )
        
        if dispositivo and dispositivo.id_persona == current_usuario.id_persona:
            await crud_dispositivo_usuario.dispositivo_usuario.delete(db, dispositivo.id)
            await db.commit()
            
            return TokenFCMResponse(
                success=True,
                message="Token FCM eliminado exitosamente"
            )
        
        return TokenFCMResponse(
            success=True,
            message="Token FCM no encontrado o no pertenece al usuario"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando token FCM: {str(e)}"
        )

@router.get("/test-notification")
async def test_notification(
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de prueba para enviar notificación al usuario actual
    Detecta automáticamente si usar Web Push o FCM
    """
    from app.services.web_push_service import web_push_service
    
    # Log de debug de claves VAPID
    logger.info(f"🔑 Clave pública VAPID en uso: {web_push_service.vapid_public_key}")
    logger.info(f"🔑 Clave privada path: {web_push_service.vapid_private_key_path}")
    
    try:
        # Intentar enviar con Web Push primero (para navegadores web)
        subscriptions = await web_push_service.obtener_suscripciones_persona(db, current_usuario.id_persona)
        
        if subscriptions:
            logger.info(f"📱 Enviando notificación Web Push a {len(subscriptions)} suscripción(es)")
            success_web = await web_push_service.enviar_notificacion_web_push(
                subscriptions=subscriptions,
                titulo="Notificación de Prueba",
                mensaje="Esta es una notificación de prueba del sistema",
                datos_extra={"tipo": "test", "timestamp": str(int(__import__('time').time()))}
            )
            
            if success_web:
                logger.info("✅ Notificación Web Push enviada exitosamente")
                return {
                    "success": True,
                    "message": "Notificación Web Push enviada exitosamente",
                    "method": "web_push",
                    "subscriptions_count": len(subscriptions),
                    "debug": {
                        "usuario_id": current_usuario.id,
                        "persona_id": current_usuario.id_persona
                    }
                }
            else:
                logger.warning("⚠️ Falló el envío de notificación Web Push")
                return {
                    "success": False,
                    "message": "Error enviando notificación Web Push",
                    "method": "web_push",
                    "subscriptions_count": len(subscriptions)
                }
        
        # Si no hay suscripciones Web Push, retornar error
        logger.warning(f"⚠️ Usuario {current_usuario.id} no tiene suscripciones registradas")
        return {
            "success": False, 
            "message": "No hay suscripciones Web Push ni tokens FCM registrados",
            "debug": {
                "usuario_id": current_usuario.id,
                "persona_id": current_usuario.id_persona,
                "subscriptions_count": 0
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error en test_notification: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/debug-tokens")
async def debug_tokens(
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de debug para ver todos los tokens registrados
    """
    from app.services.notification_service import notification_service
    from sqlalchemy import select, text
    
    try:
        # Verificar estructura de la tabla primero
        verificacion_tabla = {}
        try:
            # Intentar consultar la tabla con todas las columnas esperadas
            result = await db.execute(
                text("SELECT id, token_fcm, id_persona, plataforma, activo, fecha_registro, fecha_ultima_actividad FROM dispositivo_usuario LIMIT 1")
            )
            verificacion_tabla["estructura_correcta"] = True
            verificacion_tabla["columnas_verificadas"] = ["id", "token_fcm", "id_persona", "plataforma", "activo", "fecha_registro", "fecha_ultima_actividad"]
        except Exception as e:
            verificacion_tabla["estructura_correcta"] = False
            verificacion_tabla["error"] = str(e)
            verificacion_tabla["mensaje"] = "⚠️ La tabla dispositivo_usuario no tiene la estructura correcta. Ejecuta 'alembic upgrade head' en el backend."
        
        # Ver tokens del usuario actual
        tokens = []
        try:
            tokens = await notification_service.obtener_tokens_persona(db, current_usuario.id_persona)
        except Exception as e:
            tokens = []
            verificacion_tabla["error_obteniendo_tokens"] = str(e)
        
        # Ver todos los dispositivos registrados en la BD
        todos_dispositivos = []
        try:
            result = await db.execute(select(DispositivoUsuario))
            todos_dispositivos = result.scalars().all()
        except Exception as e:
            verificacion_tabla["error_listando_dispositivos"] = str(e)
        
        # Si el usuario tiene un taller, ver tokens del taller
        tokens_taller = []
        taller_info = None
        roles_usuario = []
        
        from app.models.rol_usuario import RolUsuario
        from app.models.rol import Rol
        result_rol = await db.execute(
            select(RolUsuario, Rol).join(Rol, RolUsuario.id_rol == Rol.id).where(
                RolUsuario.id_usuario == current_usuario.id
            )
        )
        roles_usuario = result_rol.all()
        
        # Buscar el primer rol que tenga un taller asociado
        for rol_usuario, rol in roles_usuario:
            if rol_usuario.id_taller:
                taller_info = rol_usuario.id_taller
                try:
                    tokens_taller = await notification_service.obtener_tokens_usuarios_taller(
                        db, rol_usuario.id_taller
                    )
                except Exception as e:
                    verificacion_tabla["error_tokens_taller"] = str(e)
                break
        
        return {
            "verificacion_tabla": verificacion_tabla,
            "usuario_actual": {
                "id": current_usuario.id,
                "nombre": current_usuario.nombre,
                "persona_id": current_usuario.id_persona,
                "tokens": [t[:20] + "..." for t in tokens],
                "tokens_count": len(tokens),
                "roles": [
                    {
                        "rol_nombre": rol.nombre,
                        "id_taller": rol_usuario.id_taller
                    }
                    for rol_usuario, rol in roles_usuario
                ]
            },
            "taller": {
                "id_taller": taller_info,
                "tokens_count": len(tokens_taller),
                "tokens": [t[:20] + "..." for t in tokens_taller]
            } if taller_info else None,
            "todos_dispositivos": {
                "total": len(todos_dispositivos),
                "dispositivos": [
                    {
                        "id": d.id,
                        "persona_id": d.id_persona,
                        "token_preview": d.token_fcm[:20] + "..." if d.token_fcm else None
                    }
                    for d in todos_dispositivos
                ]
            }
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "mensaje": "⚠️ Error al consultar la base de datos. Es probable que necesites ejecutar las migraciones: 'alembic upgrade head'"
        }


@router.post("/assign-taller-role")
async def assign_taller_role(
    id_taller: int = None,
    nombre_taller: str = None,
    rol_nombre: str = "admin_taller",
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Asigna manualmente un rol de taller al usuario actual.
    Útil para propósitos de desarrollo/testing.
    Puede especificar el taller por ID o por nombre.
    """
    from app.crud.crud_rol import rol as crud_rol
    from app.crud.crud_taller import taller as crud_taller
    from sqlalchemy import select
    
    try:
        # Obtener el taller
        if nombre_taller:
            result = await db.execute(
                select(Taller).where(Taller.nombre == nombre_taller)
            )
            taller = result.scalar_one_or_none()
            if not taller:
                return {"success": False, "error": f"Taller '{nombre_taller}' no encontrado"}
            id_taller = taller.id
        elif id_taller:
            taller = await crud_taller.get(db, id_taller)
            if not taller:
                return {"success": False, "error": f"Taller con ID {id_taller} no encontrado"}
        else:
            return {"success": False, "error": "Debe especificar id_taller o nombre_taller"}
        
        # Obtener el rol
        rol = await crud_rol.get_by_nombre(db, rol_nombre)
        if not rol:
            return {"success": False, "error": f"Rol '{rol_nombre}' no encontrado"}
        
        # Verificar si ya tiene el rol en ese taller
        has_rol = await crud_rol_usuario.user_has_rol(db, current_usuario.id, rol.id, id_taller)
        if has_rol:
            return {"success": True, "message": f"Ya tienes el rol '{rol_nombre}' en el taller {taller.nombre}"}
        
        # Asignar el rol
        await crud_rol_usuario.add_rol(db, current_usuario.id, rol.id, id_taller)
        await db.commit()
        
        return {
            "success": True,
            "message": f"Rol '{rol_nombre}' asignado exitosamente al taller {taller.nombre}",
            "usuario_id": current_usuario.id,
            "rol_id": rol.id,
            "taller_id": id_taller,
            "taller_nombre": taller.nombre
        }
    except Exception as e:
        await db.rollback()
        return {"success": False, "error": str(e)}


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Respuesta del health check"""
    status: str  # "healthy", "degraded", "unhealthy"
    fcm_configured: bool
    fcm_credentials_valid: bool
    fcm_access_token_valid: bool
    database_connected: bool
    details: dict

@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """
    Verifica el estado de salud del sistema de notificaciones.
    
    Checks:
    - Configuración de FCM (credentials y project_id)
    - Validez de las credenciales de FCM
    - Capacidad de obtener access token
    - Conectividad con la base de datos
    
    Returns:
        - healthy: Todos los checks pasaron
        - degraded: Algunos checks fallaron pero el sistema puede funcionar parcialmente
        - unhealthy: Checks críticos fallaron, el sistema no puede funcionar
    """
    from app.services.notification_service import notification_service
    
    # Inicializar resultado
    checks = {
        "fcm_configured": False,
        "fcm_credentials_valid": False,
        "fcm_access_token_valid": False,
        "database_connected": False
    }
    details = {}
    
    # Check 1: Verificar configuración de FCM
    if notification_service.fcm_credentials_path and notification_service.project_id:
        checks["fcm_configured"] = True
        details["fcm_project_id"] = notification_service.project_id
    else:
        details["fcm_error"] = "FCM no configurado (falta credentials_path o project_id)"
    
    # Check 2: Verificar credenciales de FCM
    if checks["fcm_configured"]:
        try:
            import os
            credentials_path = notification_service.fcm_credentials_path
            
            # Resolver ruta relativa
            if not os.path.isabs(credentials_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                credentials_path = os.path.join(base_dir, credentials_path)
            
            # Verificar que el archivo existe
            if os.path.exists(credentials_path):
                checks["fcm_credentials_valid"] = True
                details["credentials_path"] = credentials_path
            else:
                details["credentials_error"] = f"Archivo de credenciales no encontrado: {credentials_path}"
        except Exception as e:
            details["credentials_error"] = str(e)
    
    # Check 3: Verificar capacidad de obtener access token
    if checks["fcm_credentials_valid"]:
        try:
            access_token = notification_service._get_access_token()
            if access_token:
                checks["fcm_access_token_valid"] = True
                details["access_token_length"] = len(access_token)
            else:
                details["access_token_error"] = "No se pudo obtener access token"
        except Exception as e:
            details["access_token_error"] = str(e)
    
    # Check 4: Verificar conectividad con base de datos
    try:
        # Intentar una consulta simple
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        if result:
            checks["database_connected"] = True
            details["database_status"] = "connected"
    except Exception as e:
        details["database_error"] = str(e)
    
    # Determinar estado general
    if all(checks.values()):
        status = "healthy"
    elif checks["fcm_configured"] and checks["database_connected"]:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthCheckResponse(
        status=status,
        fcm_configured=checks["fcm_configured"],
        fcm_credentials_valid=checks["fcm_credentials_valid"],
        fcm_access_token_valid=checks["fcm_access_token_valid"],
        database_connected=checks["database_connected"],
        details=details
    )