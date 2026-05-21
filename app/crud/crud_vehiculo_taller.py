from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.crud.base import CRUDBase
from app.models.vehiculo_taller import VehiculoTaller, EstadoVehiculoTaller
from typing import Any


class CRUDVehiculoTaller(CRUDBase[VehiculoTaller]):
    async def get_by_matricula(self, db: AsyncSession, matricula: str) -> Optional[VehiculoTaller]:
        if not matricula:
            return None
        result = await db.execute(select(VehiculoTaller).where(func.upper(VehiculoTaller.matricula) == matricula.upper()))
        return result.scalar_one_or_none()

    async def get_by_taller(
        self,
        db: AsyncSession,
        id_taller: int,
        estado: Optional[EstadoVehiculoTaller] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[VehiculoTaller], int]:
        query = select(VehiculoTaller).where(VehiculoTaller.id_taller == id_taller)
        if estado:
            query = query.where(VehiculoTaller.estado == estado)

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        query = query.offset(skip).limit(limit).order_by(VehiculoTaller.id.desc())
        result = await db.execute(query)
        items = result.scalars().all()
        return items, total


vehiculo_taller = CRUDVehiculoTaller(VehiculoTaller)
