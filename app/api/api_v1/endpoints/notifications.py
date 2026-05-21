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