from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.vehiculo import Vehiculo

class CRUDVehiculo(CRUDBase[Vehiculo]):
    async def get_by_matricula(self, db: AsyncSession, matricula: str) -> Optional[Vehiculo]:
        result = await db.execute(select(Vehiculo).where(Vehiculo.matricula == matricula))
        return result.scalar_one_or_none()

    async def get_by_persona_paginated(
        self, db: AsyncSession, id_persona: int, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Vehiculo], int]:
        # Total de registros para la persona
        total_result = await db.execute(
            select(func.count()).select_from(Vehiculo).where(Vehiculo.id_persona == id_persona)
        )
        total = total_result.scalar_one()
        # Lista paginada
        result = await db.execute(
            select(Vehiculo)
            .where(Vehiculo.id_persona == id_persona)
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()
        return items, total

vehiculo = CRUDVehiculo(Vehiculo)