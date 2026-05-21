from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.permiso import Permiso

class CRUDPermiso(CRUDBase[Permiso]):
    async def get_by_concepto(self, db: AsyncSession, concepto: str) -> Optional[Permiso]:
        result = await db.execute(select(Permiso).where(Permiso.concepto == concepto))
        return result.scalar_one_or_none()

    async def get_multi_by_conceptos(self, db: AsyncSession, conceptos: List[str]) -> List[Permiso]:
        result = await db.execute(select(Permiso).where(Permiso.concepto.in_(conceptos)))
        return result.scalars().all()

permiso = CRUDPermiso(Permiso)