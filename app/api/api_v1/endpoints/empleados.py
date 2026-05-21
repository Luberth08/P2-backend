from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoListResponse
from app.services import empleado_service
from app.core.deps import get_current_usuario, require_permiso_en_taller
from app.models.usuario import Usuario
from typing import Optional

router = APIRouter(prefix="/talleres/{taller_id}/empleados", tags=["Empleados de Taller"])

@router.post("/", response_model=EmpleadoResponse, status_code=status.HTTP_201_CREATED)
async def crear_empleado(
    taller_id: int,
    req: EmpleadoCreate,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_empleados")),
    db: AsyncSession = Depends(get_db)
):
    return await empleado_service.create_empleado(db, taller_id, req, current_usuario.id)

@router.get("/", response_model=EmpleadoListResponse)
async def listar_empleados(
    taller_id: int,
    estado: Optional[str] = Query(None, description="Filtrar por estado (activo, suspendido)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:ver_empleados")),
    db: AsyncSession = Depends(get_db)
):
    items, total = await empleado_service.list_empleados(db, taller_id, estado, skip, limit)
    return EmpleadoListResponse(items=items, total=total, skip=skip, limit=limit)

@router.put("/{empleado_id}/suspender", response_model=EmpleadoResponse)
async def suspender_empleado(
    taller_id: int,
    empleado_id: int,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_empleados")),
    db: AsyncSession = Depends(get_db)
):
    return await empleado_service.suspender_empleado(db, empleado_id, taller_id)