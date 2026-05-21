from fastapi import APIRouter, Depends, Query, status, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_usuario
from app.models.usuario import Usuario
from app.services.categoria_incidente_service import (
    list_categorias,
    create_categoria,
    update_categoria,
    delete_categoria,
    get_categoria_by_id,
)
from app.schemas.categoria_incidente import (
    CategoriaIncidenteResponse,
    CategoriaIncidenteCreate,
    CategoriaIncidenteUpdate,
    CategoriaIncidenteListResponse,
)
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


@router.get("/", response_model=CategoriaIncidenteListResponse)
async def listar_categorias(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    items, total = await list_categorias(db, skip, limit)
    return CategoriaIncidenteListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{categoria_id}", response_model=CategoriaIncidenteResponse)
async def obtener_categoria(
    categoria_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    return await get_categoria_by_id(db, categoria_id)


@router.post("/", response_model=CategoriaIncidenteResponse, status_code=status.HTTP_201_CREATED)
async def crear_categoria(
    req: CategoriaIncidenteCreate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    return await create_categoria(db, req)


@router.put("/{categoria_id}", response_model=CategoriaIncidenteResponse)
async def actualizar_categoria(
    categoria_id: int,
    req: CategoriaIncidenteUpdate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    return await update_categoria(db, categoria_id, req)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_categoria(
    categoria_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    await delete_categoria(db, categoria_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
