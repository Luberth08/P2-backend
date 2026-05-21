from fastapi import APIRouter, Depends, Query, status, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_usuario
from app.models.usuario import Usuario
from app.services import taller_service
from app.schemas.taller import TallerResponse, TallerDetailResponse, TallerUpdate
from app.crud.crud_rol import rol as crud_rol
from app.crud.crud_rol_usuario import rol_usuario as crud_rol_usuario
from app.core.constants import ROL_ADMIN_SISTEMA

router = APIRouter(tags=["Talleres"])


@router.get("/mis-talleres", response_model=dict)
async def list_mis_talleres(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Lista los talleres donde el usuario es admin_taller o super_admin_taller"""
    items, total = await taller_service.list_mis_talleres(db, current_usuario.id, skip, limit)
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{taller_id}", response_model=TallerDetailResponse)
async def get_taller_detail(
    taller_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el detalle completo de un taller específico.
    Requiere ser admin_taller o super_admin_taller del taller.
    """
    return await taller_service.get_taller_detail(db, taller_id, current_usuario.id)


@router.put("/{taller_id}", response_model=TallerDetailResponse)
async def update_taller(
    taller_id: int,
    data: TallerUpdate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza la información de un taller.
    Solo super_admin_taller puede editar.
    """
    return await taller_service.update_taller(db, taller_id, current_usuario.id, data)


@router.get("/", response_model=dict)
async def listar_talleres_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    estado: str | None = Query(None, description="Filtrar por estado: 'activo'|'suspendido'"),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los talleres (solo admin_sistema)"""
    # Verificar rol admin sistema
    rol_rec = await crud_rol.get_by_nombre(db, ROL_ADMIN_SISTEMA)
    if not rol_rec:
        raise HTTPException(status_code=500, detail=f"Rol '{ROL_ADMIN_SISTEMA}' no encontrado")
    has = await crud_rol_usuario.user_has_rol(db, current_usuario.id, rol_rec.id)
    if not has:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido")

    items, total = await taller_service.list_all_talleres_admin(db, skip=skip, limit=limit, estado=estado)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.put("/{taller_id}/suspender", response_model=TallerResponse)
async def suspender_taller_endpoint(
    taller_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Suspende un taller (solo admin_sistema)"""
    rol_rec = await crud_rol.get_by_nombre(db, ROL_ADMIN_SISTEMA)
    if not rol_rec:
        raise HTTPException(status_code=500, detail=f"Rol '{ROL_ADMIN_SISTEMA}' no encontrado")
    has = await crud_rol_usuario.user_has_rol(db, current_usuario.id, rol_rec.id)
    if not has:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido")

    return await taller_service.suspend_taller(db, taller_id)


@router.put("/{taller_id}/activar", response_model=TallerResponse)
async def activar_taller_endpoint(
    taller_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """Activa un taller suspendido (solo admin_sistema)"""
    rol_rec = await crud_rol.get_by_nombre(db, ROL_ADMIN_SISTEMA)
    if not rol_rec:
        raise HTTPException(status_code=500, detail=f"Rol '{ROL_ADMIN_SISTEMA}' no encontrado")
    has = await crud_rol_usuario.user_has_rol(db, current_usuario.id, rol_rec.id)
    if not has:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido")

    return await taller_service.activar_taller(db, taller_id)