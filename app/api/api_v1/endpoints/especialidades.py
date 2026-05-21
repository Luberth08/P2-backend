from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_usuario, require_permiso
from app.models.usuario import Usuario
from app.schemas.especialidad import (
    EspecialidadResponse,
    EspecialidadCreate,
    EspecialidadUpdate,
    EspecialidadListResponse,
)
from app.services.especialidad_service import (
    list_especialidades,
    create_especialidad,
    update_especialidad,
    delete_especialidad,
)

router = APIRouter(prefix="/especialidades", tags=["Especialidades"])


@router.get("/", response_model=EspecialidadListResponse)
async def listar_especialidades_endpoint(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(10, ge=1, le=1000, description="Registros por página"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_especialidades(db, skip, limit)
    return EspecialidadListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("/", response_model=EspecialidadResponse, status_code=status.HTTP_201_CREATED)
async def crear_especialidad_endpoint(
    req: EspecialidadCreate,
    current_usuario: Usuario = Depends(require_permiso("especialidad:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    return await create_especialidad(db, req)


@router.put("/{especialidad_id}", response_model=EspecialidadResponse)
async def actualizar_especialidad_endpoint(
    especialidad_id: int,
    req: EspecialidadUpdate,
    current_usuario: Usuario = Depends(require_permiso("especialidad:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    return await update_especialidad(db, especialidad_id, req)


@router.delete("/{especialidad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_especialidad_endpoint(
    especialidad_id: int,
    current_usuario: Usuario = Depends(require_permiso("especialidad:gestionar")),
    db: AsyncSession = Depends(get_db),
):
    await delete_especialidad(db, especialidad_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)