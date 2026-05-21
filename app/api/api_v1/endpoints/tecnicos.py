from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.tecnico import TecnicoCreate, TecnicoResponse, TecnicoListResponse, TecnicoEspecialidadesUpdate
from app.services import tecnico_service
from app.core.deps import get_current_usuario, require_permiso_en_taller
from app.models.usuario import Usuario
from typing import Optional

router = APIRouter(prefix="/talleres/{taller_id}/tecnicos", tags=["Técnicos de Taller"])

@router.post("/", response_model=TecnicoResponse, status_code=status.HTTP_201_CREATED)
async def crear_tecnico(
    taller_id: int,
    req: TecnicoCreate,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_tecnicos")),
    db: AsyncSession = Depends(get_db)
):
    return await tecnico_service.create_tecnico(db, taller_id, req, current_usuario.id)

@router.get("/", response_model=TecnicoListResponse)
async def listar_tecnicos(
    taller_id: int,
    estado: Optional[str] = Query(None, description="Filtrar por estado (disponible, suspendido)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:ver_tecnicos")),
    db: AsyncSession = Depends(get_db)
):
    items, total = await tecnico_service.list_tecnicos(db, taller_id, estado, skip, limit)
    return TecnicoListResponse(items=items, total=total, skip=skip, limit=limit)

@router.put("/{tecnico_id}/suspender", response_model=TecnicoResponse)
async def suspender_tecnico(
    taller_id: int,
    tecnico_id: int,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_tecnicos")),
    db: AsyncSession = Depends(get_db)
):
    return await tecnico_service.suspender_tecnico(db, tecnico_id, taller_id)


@router.put("/{tecnico_id}/especialidades", response_model=TecnicoResponse)
async def actualizar_especialidades(
    taller_id: int,
    tecnico_id: int,
    req: TecnicoEspecialidadesUpdate,
    current_usuario: Usuario = Depends(require_permiso_en_taller("taller:gestionar_tecnicos")),
    db: AsyncSession = Depends(get_db)
):
    return await tecnico_service.update_tecnico_especialidades(db, taller_id, tecnico_id, req.especialidades_ids, current_usuario.id)