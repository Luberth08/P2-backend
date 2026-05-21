from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.crud.base import CRUDBase
from app.models.configuracion_sistema import ConfiguracionSistema

class CRUDConfiguracionSistema(CRUDBase[ConfiguracionSistema]):
    async def get_by_clave(self, db: AsyncSession, clave: str) -> Optional[ConfiguracionSistema]:
        result = await db.execute(select(ConfiguracionSistema).where(ConfiguracionSistema.clave == clave))
        return result.scalar_one_or_none()

    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 10) -> Tuple[List[ConfiguracionSistema], int]:
        total_result = await db.execute(select(func.count()).select_from(ConfiguracionSistema))
        total = total_result.scalar_one()
        result = await db.execute(select(ConfiguracionSistema).offset(skip).limit(limit))
        items = result.scalars().all()
        return items, total

configuracion_sistema = CRUDConfiguracionSistema(ConfiguracionSistema)
