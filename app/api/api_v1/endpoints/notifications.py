"""
Endpoints para gestión de notificaciones push
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.core.deps import get_current_usuario
from app.models.usuario import Usuario
from app.crud import crud_dispositivo_usuario
from app.models.dispositivo_usuario import DispositivoUsuario

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])

class TokenFCMRequest(BaseModel):
    token_fcm: str

class TokenFCMResponse(BaseModel):
    success: bool
    message: str

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
    """
    from app.services.notification_service import notification_service
    
    try:
        tokens = await notification_service.obtener_tokens_persona(db, current_usuario.id_persona)
        
        if not tokens:
            return {"success": False, "message": "No hay tokens FCM registrados"}
        
        success = await notification_service.enviar_notificacion_push(
            tokens=tokens,
            titulo="Notificación de Prueba",
            mensaje="Esta es una notificación de prueba del sistema",
            datos_extra={"tipo": "test", "timestamp": str(int(__import__('time').time()))}
        )
        
        return {
            "success": success,
            "message": "Notificación enviada" if success else "Error enviando notificación",
            "tokens_count": len(tokens)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando notificación de prueba: {str(e)}"
        )


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