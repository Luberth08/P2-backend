from fastapi import APIRouter, Depends, Query, status, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_usuario
from app.models.usuario import Usuario
from app.services.tipo_incidente_service import (
    list_tipos,
    create_tipo,
    update_tipo,
    delete_tipo,
)
from app.schemas.tipo_incidente import (
    TipoIncidenteResponse,
    TipoIncidenteCreate,
    TipoIncidenteUpdate,
    TipoIncidenteListResponse,
)
from app.crud.crud_categoria_incidente import categoria_incidente as crud_categoria
from app.crud.crud_rol import rol as crud_rol
from app.crud.crud_rol_usuario import rol_usuario as crud_rol_usuario
from app.core.constants import ROL_ADMIN_SISTEMA

router = APIRouter()


async def _require_admin_system(current_usuario: Usuario, db: AsyncSession):
    r = await crud_rol.get_by_nombre(db, ROL_ADMIN_SISTEMA)
    if not r:
        raise HTTPException(status_code=500, detail=f"Rol '{ROL_ADMIN_SISTEMA}' no encontrado")
    has = await crud_rol_usuario.user_has_rol(db, current_usuario.id, r.id)
    if not has:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido")


@router.get("/", response_model=TipoIncidenteListResponse)
async def listar_tipos(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    id_categoria: Optional[int] = Query(None),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    items, total = await list_tipos(db, skip, limit, id_categoria)
    return TipoIncidenteListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("/", response_model=TipoIncidenteResponse, status_code=status.HTTP_201_CREATED)
async def crear_tipo(
    req: TipoIncidenteCreate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    return await create_tipo(db, req)


@router.put("/{tipo_id}", response_model=TipoIncidenteResponse)
async def actualizar_tipo(
    tipo_id: int,
    req: TipoIncidenteUpdate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    return await update_tipo(db, tipo_id, req)


@router.delete("/{tipo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_tipo(
    tipo_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    await delete_tipo(db, tipo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/categorias/simple", response_model=list[dict])
async def listar_categorias_simple(
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    cats = await crud_categoria.get_all(db)
    return [{"id": c.id, "nombre": c.nombre} for c in cats]
