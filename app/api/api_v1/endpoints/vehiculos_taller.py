from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.vehiculo_taller import (
    VehiculoTallerCreate,
    VehiculoTallerResponse,
    VehiculoTallerListResponse,
    VehiculoTallerUpdate,
)
from app.services.vehiculo_taller_service import vehiculo_taller_service
from app.core.deps import require_permiso_en_taller
from app.models.usuario import Usuario

router = APIRouter(prefix="/talleres/{taller_id}/vehiculos", tags=["Vehículos Taller"])


@router.post("/", response_model=VehiculoTallerResponse, status_code=status.HTTP_201_CREATED)
async def crear_vehiculo(
    taller_id: int,
    req: VehiculoTallerCreate,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_vehiculos")),
    db: AsyncSession = Depends(get_db),
):
    return await vehiculo_taller_service.create(db, taller_id, req, current_usuario.id)


@router.get("/", response_model=VehiculoTallerListResponse)
async def listar_vehiculos(
    taller_id: int,
    estado: str | None = Query(None, description="Filtrar por estado (disponible, inactivo, ...)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:ver_vehiculos")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await vehiculo_taller_service.list_by_taller(db, taller_id, estado, skip, limit)
    return VehiculoTallerListResponse(items=items, total=total, skip=skip, limit=limit)


@router.put("/{vehiculo_id}", response_model=VehiculoTallerResponse)
async def actualizar_vehiculo(
    taller_id: int,
    vehiculo_id: int,
    req: VehiculoTallerUpdate,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_vehiculos")),
    db: AsyncSession = Depends(get_db),
):
    return await vehiculo_taller_service.update(db, taller_id, vehiculo_id, req, current_usuario.id)


@router.put("/{vehiculo_id}/inactivar", response_model=VehiculoTallerResponse)
async def inactivar_vehiculo(
    taller_id: int,
    vehiculo_id: int,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_vehiculos")),
    db: AsyncSession = Depends(get_db),
):
    return await vehiculo_taller_service.set_inactive(db, taller_id, vehiculo_id, current_usuario.id)
