"""
Endpoints de sincronización offline
Permiten que los clientes (web/mobile) sincronicen datos cuando recuperan conexión
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.sync.schemas import SyncRequest, SyncResponse, SyncStatusResponse
from app.sync.service import get_sync_service

router = APIRouter(prefix="/sync", tags=["Sincronización Offline"])


@router.post("/pending", response_model=SyncResponse)
async def sync_pending_data(
    sync_request: SyncRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Sincroniza datos pendientes desde el cliente (web/mobile)
    
    Este endpoint recibe un batch de operaciones pendientes que fueron guardadas
    localmente cuando el cliente estaba offline. El servidor procesa cada operación,
    valida duplicados, detecta conflictos y ejecuta las operaciones correspondientes.
    
    **Payload esperado:**
    - **items**: Lista de operaciones a sincronizar
    - **user_id**: ID del usuario (opcional, si está autenticado)
    - **device_info**: Información del dispositivo (opcional)
    
    **Respuesta:**
    - **success**: Indica si la operación fue exitosa globalmente
    - **total_items**: Total de items procesados
    - **successful_items**: Items sincronizados exitosamente
    - **failed_items**: Items que fallaron
    - **conflicted_items**: Items con conflictos
    - **results**: Lista detallada de resultados por item
    """
    try:
        # Obtener IP del cliente para logging
        client_ip = request.client.host if request.client else None
        
        # Obtener user_id si está autenticado (opcional para este endpoint)
        user_id = sync_request.user_id
        
        # Crear servicio de sincronización
        sync_service = get_sync_service(db)
        
        # Procesar solicitud de sincronización
        result = await sync_service.process_sync_request(
            sync_request=sync_request,
            user_id=user_id,
            ip_address=client_ip
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante sincronización: {str(e)}"
        )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el estado de sincronización del cliente
    
    Retorna información sobre:
    - **pending_items**: Cantidad de items pendientes de sincronización
    - **last_sync_timestamp**: Timestamp de la última sincronización exitosa
    - **sync_in_progress**: Indica si hay sincronización en curso
    """
    try:
        sync_service = get_sync_service(db)
        status_data = await sync_service.get_sync_status(user_id=user_id)
        
        return SyncStatusResponse(**status_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estado de sincronización: {str(e)}"
        )


@router.post("/batch")
async def sync_batch(
    sync_request: SyncRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint alternativo para sincronización por lotes
    
    Similar a /sync/pending pero optimizado para grandes volúmenes de datos.
    Usa el mismo proceso pero con configuraciones diferentes para manejar
    batches más grandes.
    """
    # Por ahora, usa la misma lógica que sync/pending
    # Se puede separar la lógica en el futuro si se necesita optimización
    return await sync_pending_data(sync_request, request, db)


@router.get("/health")
async def sync_health():
    """
    Health check del módulo de sincronización
    """
    return {
        "status": "healthy",
        "module": "sync",
        "message": "Sincronización offline operativa"
    }
