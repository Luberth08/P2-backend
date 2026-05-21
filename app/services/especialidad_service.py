import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select, func
from app.models.especialidad import Especialidad
from app.models.tecnico_especialidad import TecnicoEspecialidad
from app.crud.crud_especialidad import especialidad as crud_especialidad
from app.crud.crud_requiere_especialidad import requiere_especialidad as crud_requiere
from app.schemas.especialidad import (
    EspecialidadCreate,
    EspecialidadUpdate,
    EspecialidadResponse,
)

logger = logging.getLogger(__name__)


async def list_especialidades(db: AsyncSession, skip: int = 0, limit: int = 10):
    total_result = await db.execute(select(func.count()).select_from(Especialidad))
    total = total_result.scalar_one()
    result = await db.execute(select(Especialidad).offset(skip).limit(limit))
    items = result.scalars().all()

    # Convert to response DTOs
    resp_items = [EspecialidadResponse(id=i.id, nombre=i.nombre, descripcion=i.descripcion) for i in items]
    return resp_items, total


async def create_especialidad(db: AsyncSession, data: EspecialidadCreate) -> EspecialidadResponse:
    # Verificar unicidad por nombre
    stmt = select(Especialidad).where(Especialidad.nombre == data.nombre)
    result = await db.execute(stmt)
    exists = result.scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Especialidad con ese nombre ya existe")

    nuevo = await crud_especialidad.create(db, data.dict())
    await db.commit()
    return EspecialidadResponse(id=nuevo.id, nombre=nuevo.nombre, descripcion=nuevo.descripcion)


async def update_especialidad(db: AsyncSession, id: int, data: EspecialidadUpdate) -> EspecialidadResponse:
    obj = await crud_especialidad.get(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")

    # Si cambia el nombre, verificar unicidad
    if data.nombre and data.nombre != obj.nombre:
        stmt = select(Especialidad).where(Especialidad.nombre == data.nombre)
        res = await db.execute(stmt)
        other = res.scalar_one_or_none()
        if other:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Otra especialidad ya usa ese nombre")

    update_data = {k: v for k, v in data.dict().items() if v is not None}
    updated = await crud_especialidad.update(db, obj, update_data)
    await db.commit()
    return EspecialidadResponse(id=updated.id, nombre=updated.nombre, descripcion=updated.descripcion)


async def delete_especialidad(db: AsyncSession, id: int) -> None:
    # Verificar relaciones en tecnico_especialidad
    stmt = select(func.count()).select_from(TecnicoEspecialidad).where(TecnicoEspecialidad.id_especialidad == id)
    res = await db.execute(stmt)
    relaciones = res.scalar_one()
    if relaciones and relaciones > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede eliminar: existen técnicos asociados a esta especialidad")
    
    # Verificar relaciones en requiere_especialidad (categorías que requieren esta especialidad)
    categorias = await crud_requiere.get_categorias_by_especialidad(db, id)
    if categorias and len(categorias) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar: existen categorías de incidente que requieren esta especialidad"
        )

    deleted = await crud_especialidad.delete(db, id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")
    await db.commit()
    return None
