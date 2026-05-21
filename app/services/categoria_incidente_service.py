from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from typing import List, Tuple
from app.crud.crud_categoria_incidente import categoria_incidente as crud_categoria
from app.crud.crud_tipo_incidente import tipo_incidente as crud_tipo
from app.crud.crud_especialidad import especialidad as crud_especialidad
from app.crud.crud_requiere_especialidad import requiere_especialidad as crud_requiere
from app.schemas.categoria_incidente import (
    CategoriaIncidenteCreate,
    CategoriaIncidenteUpdate,
    CategoriaIncidenteResponse,
)


async def get_categoria_by_id(db: AsyncSession, id: int) -> CategoriaIncidenteResponse:
    """Obtiene una categoría por su ID con sus especialidades"""
    obj = await crud_categoria.get(db, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    
    especialidad_ids = await crud_requiere.get_especialidades_by_categoria(db, id)
    
    return CategoriaIncidenteResponse(
        id=obj.id,
        nombre=obj.nombre,
        especialidad_ids=especialidad_ids
    )


async def list_categorias(db: AsyncSession, skip: int = 0, limit: int = 10) -> Tuple[List[CategoriaIncidenteResponse], int]:
    total = await crud_categoria.count(db)
    items = await crud_categoria.get_all(db, skip=skip, limit=limit)
    
    # Obtener especialidades para cada categoría
    resp = []
    for item in items:
        especialidad_ids = await crud_requiere.get_especialidades_by_categoria(db, item.id)
        resp.append(CategoriaIncidenteResponse(
            id=item.id,
            nombre=item.nombre,
            especialidad_ids=especialidad_ids
        ))
    
    return resp, total


async def create_categoria(db: AsyncSession, data: CategoriaIncidenteCreate) -> CategoriaIncidenteResponse:
    # Validar que la categoría no exista
    existing = await crud_categoria.get_by_nombre(db, data.nombre)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categoría con ese nombre ya existe"
        )
    
    # Validar que todas las especialidades existan
    for esp_id in data.especialidad_ids:
        especialidad = await crud_especialidad.get(db, esp_id)
        if not especialidad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Especialidad con ID {esp_id} no existe"
            )
    
    # Crear la categoría
    obj = await crud_categoria.create(db, {"nombre": data.nombre})
    
    # Asociar las especialidades
    await crud_requiere.set_especialidades_for_categoria(db, obj.id, data.especialidad_ids)
    
    await db.commit()
    
    return CategoriaIncidenteResponse(
        id=obj.id,
        nombre=obj.nombre,
        especialidad_ids=data.especialidad_ids
    )


async def update_categoria(db: AsyncSession, id: int, data: CategoriaIncidenteUpdate) -> CategoriaIncidenteResponse:
    obj = await crud_categoria.get(db, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    
    # Validar nombre único si se está actualizando
    if data.nombre and data.nombre != obj.nombre:
        other = await crud_categoria.get_by_nombre(db, data.nombre)
        if other:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Otra categoría ya usa ese nombre"
            )
    
    # Validar especialidades si se están actualizando
    if data.especialidad_ids is not None:
        for esp_id in data.especialidad_ids:
            especialidad = await crud_especialidad.get(db, esp_id)
            if not especialidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Especialidad con ID {esp_id} no existe"
                )
        
        # Actualizar especialidades
        await crud_requiere.set_especialidades_for_categoria(db, id, data.especialidad_ids)
    
    # Actualizar nombre si se proporcionó
    if data.nombre:
        updated = await crud_categoria.update(db, obj, {"nombre": data.nombre})
    else:
        updated = obj
    
    # Obtener especialidades actuales
    especialidad_ids = await crud_requiere.get_especialidades_by_categoria(db, id)
    
    await db.commit()
    
    return CategoriaIncidenteResponse(
        id=updated.id,
        nombre=updated.nombre,
        especialidad_ids=especialidad_ids
    )


async def delete_categoria(db: AsyncSession, id: int) -> None:
    # Verificar si existen tipos asociados
    stmt = select(func.count()).select_from(crud_tipo.model).where(crud_tipo.model.id_categoria_incidente == id)
    res = await db.execute(stmt)
    count = res.scalar_one()
    if count and count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar: existen tipos de incidentes asociados"
        )
    
    # Las especialidades se eliminarán automáticamente por CASCADE
    deleted = await crud_categoria.delete(db, id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada"
        )
    
    await db.commit()
    return None
