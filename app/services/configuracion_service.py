from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func
from app.crud.crud_configuracion_sistema import configuracion_sistema as crud_config
from app.schemas.configuracion import (
    ConfiguracionCreate,
    ConfiguracionUpdate,
    ConfiguracionResponse,
)

async def list_configuraciones(db: AsyncSession, skip: int = 0, limit: int = 10) -> Tuple[List[ConfiguracionResponse], int]:
    total = await crud_config.count(db)
    items, _ = await crud_config.get_paginated(db, skip=skip, limit=limit)
    resp = [ConfiguracionResponse(id=i.id, clave=i.clave, valor=i.valor, id_usuario=i.id_usuario) for i in items]
    return resp, total


async def create_configuracion(db: AsyncSession, data: ConfiguracionCreate, id_usuario: int) -> ConfiguracionResponse:
    existing = await crud_config.get_by_clave(db, data.clave)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clave ya existe")
    payload = data.dict()
    payload["id_usuario"] = id_usuario
    obj = await crud_config.create(db, payload)
    await db.commit()
    return ConfiguracionResponse(id=obj.id, clave=obj.clave, valor=obj.valor, id_usuario=obj.id_usuario)


async def update_configuracion(db: AsyncSession, id: int, data: ConfiguracionUpdate, id_usuario: int) -> ConfiguracionResponse:
    obj = await crud_config.get(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuración no encontrada")
    update_data = {"valor": data.valor, "id_usuario": id_usuario}
    updated = await crud_config.update(db, obj, update_data)
    await db.commit()
    return ConfiguracionResponse(id=updated.id, clave=updated.clave, valor=updated.valor, id_usuario=updated.id_usuario)


async def delete_configuracion(db: AsyncSession, id: int) -> None:
    deleted = await crud_config.delete(db, id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuración no encontrada")
    await db.commit()
    return None
