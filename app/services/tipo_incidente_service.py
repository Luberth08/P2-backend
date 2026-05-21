from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from typing import List, Tuple, Optional
from app.crud.crud_tipo_incidente import tipo_incidente as crud_tipo
from app.crud.crud_categoria_incidente import categoria_incidente as crud_categoria
from app.crud.crud_incidente import incidente as crud_incidente
from app.schemas.tipo_incidente import (
    TipoIncidenteCreate,
    TipoIncidenteUpdate,
    TipoIncidenteResponse,
)


async def list_tipos(db: AsyncSession, skip: int = 0, limit: int = 10, id_categoria: Optional[int] = None) -> Tuple[List[TipoIncidenteResponse], int]:
    # contar con filtro
    # evitar lazy-load en el bucle: precargar la relación `categoria`
    stmt = select(crud_tipo.model).options(selectinload(crud_tipo.model.categoria))
    if id_categoria:
        stmt = stmt.where(crud_tipo.model.id_categoria_incidente == id_categoria)
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar_one()
    result = await db.execute(stmt.offset(skip).limit(limit))
    items = result.scalars().all()
    resp = []
    for t in items:
        categoria_nombre = t.categoria.nombre if t.categoria else None
        resp.append(TipoIncidenteResponse(id=t.id, concepto=t.concepto, prioridad=t.prioridad, requiere_remolque=t.requiere_remolque, id_categoria_incidente=t.id_categoria_incidente, categoria_nombre=categoria_nombre))
    return resp, total


async def create_tipo(db: AsyncSession, data: TipoIncidenteCreate) -> TipoIncidenteResponse:
    # Unicidad concepto
    existing = await crud_tipo.get_by_concepto(db, data.concepto)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de incidente con ese concepto ya existe")

    # Si se indicó categoria, verificar existencia
    if data.id_categoria_incidente:
        cat = await crud_categoria.get(db, data.id_categoria_incidente)
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoría indicada no existe")

    obj = await crud_tipo.create(db, data.dict())
    await db.commit()
    # evitar lazy-load; si validamos la categoría antes, consultarla directamente
    categoria_nombre = None
    if data.id_categoria_incidente:
        cat = await crud_categoria.get(db, data.id_categoria_incidente)
        categoria_nombre = cat.nombre if cat else None
    return TipoIncidenteResponse(id=obj.id, concepto=obj.concepto, prioridad=obj.prioridad, requiere_remolque=obj.requiere_remolque, id_categoria_incidente=obj.id_categoria_incidente, categoria_nombre=categoria_nombre)


async def update_tipo(db: AsyncSession, id: int, data: TipoIncidenteUpdate) -> TipoIncidenteResponse:
    obj = await crud_tipo.get(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo no encontrado")

    if data.concepto and data.concepto != obj.concepto:
        other = await crud_tipo.get_by_concepto(db, data.concepto)
        if other:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Otro tipo ya usa ese concepto")

    if data.id_categoria_incidente:
        cat = await crud_categoria.get(db, data.id_categoria_incidente)
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoría indicada no existe")

    update_data = {k: v for k, v in data.dict().items() if v is not None}
    updated = await crud_tipo.update(db, obj, update_data)
    await db.commit()
    # evitar lazy-load para la categoría
    categoria_nombre = None
    if updated.id_categoria_incidente:
        cat = await crud_categoria.get(db, updated.id_categoria_incidente)
        categoria_nombre = cat.nombre if cat else None
    return TipoIncidenteResponse(id=updated.id, concepto=updated.concepto, prioridad=updated.prioridad, requiere_remolque=updated.requiere_remolque, id_categoria_incidente=updated.id_categoria_incidente, categoria_nombre=categoria_nombre)


async def delete_tipo(db: AsyncSession, id: int) -> None:
    # Verificar incidentes asociados
    stmt = select(func.count()).select_from(crud_incidente.model).where(crud_incidente.model.id_tipo_incidente == id)
    res = await db.execute(stmt)
    count = res.scalar_one()
    if count and count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede eliminar: existen incidentes que referencian este tipo")
    deleted = await crud_tipo.delete(db, id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo no encontrado")
    await db.commit()
    return None
