from fastapi import APIRouter, Depends, Query, status, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_usuario
from app.models.usuario import Usuario
from app.services.configuracion_service import (
    list_configuraciones,
    create_configuracion,
    update_configuracion,
    delete_configuracion,
)
from app.schemas.configuracion import (
    ConfiguracionResponse,
    ConfiguracionCreate,
    ConfiguracionUpdate,
    ConfiguracionListResponse,
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


@router.get("/", response_model=ConfiguracionListResponse)
async def listar_configuraciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    items, total = await list_configuraciones(db, skip, limit)
    return ConfiguracionListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("/", response_model=ConfiguracionResponse, status_code=status.HTTP_201_CREATED)
async def crear_configuracion(
    req: ConfiguracionCreate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    return await create_configuracion(db, req, current_usuario.id)


@router.put("/{config_id}", response_model=ConfiguracionResponse)
async def actualizar_configuracion(
    config_id: int,
    req: ConfiguracionUpdate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    return await update_configuracion(db, config_id, req, current_usuario.id)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_configuracion(
    config_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin_system(current_usuario, db)
    await delete_configuracion(db, config_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
