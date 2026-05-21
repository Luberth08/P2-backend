from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.solicitud import (
    SolicitudAfiliacionCreate, SolicitudAfiliacionResponse, 
    SolicitudAfiliacionUpdateEstado, SolicitudListResponse
)
from app.services import solicitud_service
from app.core.deps import get_current_usuario, require_permiso
from app.models.usuario import Usuario

router = APIRouter(tags=["Afiliación de Talleres"])

@router.post("/", response_model=SolicitudAfiliacionResponse, status_code=status.HTTP_201_CREATED)
async def crear_solicitud(
    req: SolicitudAfiliacionCreate,
    current_usuario: Usuario = Depends(require_permiso("solicitud:crear")),
    db: AsyncSession = Depends(get_db)
):
    return await solicitud_service.create_solicitud(db, current_usuario.id, req)

@router.get("/mis-solicitudes", response_model=SolicitudListResponse)
async def mis_solicitudes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    items, total = await solicitud_service.list_mis_solicitudes(db, current_usuario.id, skip, limit)
    return SolicitudListResponse(items=items, total=total, skip=skip, limit=limit)

@router.get("/", response_model=SolicitudListResponse)
async def listar_todas_solicitudes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    _: Usuario = Depends(require_permiso("solicitud:revisar")),
    db: AsyncSession = Depends(get_db)
):
    items, total = await solicitud_service.list_all_solicitudes(db, skip, limit)
    return SolicitudListResponse(items=items, total=total, skip=skip, limit=limit)

@router.put("/{solicitud_id}/estado", response_model=SolicitudAfiliacionResponse)
async def cambiar_estado_solicitud(
    solicitud_id: int,
    req: SolicitudAfiliacionUpdateEstado,
    current_usuario: Usuario = Depends(require_permiso("solicitud:revisar")),
    db: AsyncSession = Depends(get_db)
):
    return await solicitud_service.update_solicitud_estado(db, solicitud_id, req.estado, current_usuario.id, req.comentario_revision)

@router.get("/pendientes", response_model=SolicitudListResponse)
async def listar_solicitudes_pendientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    _: Usuario = Depends(require_permiso("solicitud:revisar")),
    db: AsyncSession = Depends(get_db)
):
    items, total = await solicitud_service.list_solicitudes_pendientes(db, skip, limit)
    return SolicitudListResponse(items=items, total=total, skip=skip, limit=limit)