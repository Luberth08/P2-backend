from app.crud.base import CRUDBase
from sqlalchemy import select
from app.models.especialidad import Especialidad
from sqlalchemy.ext.asyncio import AsyncSession

class CRUDEspecialidad(CRUDBase[Especialidad]):
    async def get_all(self, db: AsyncSession):
        result = await db.execute(select(Especialidad))
        return result.scalars().all()

    async def get_multi_by_ids(self, db: AsyncSession, ids: list[int]):
        if not ids:
            return []
        result = await db.execute(select(Especialidad).where(Especialidad.id.in_(ids)))
        return result.scalars().all()
especialidad = CRUDEspecialidad(Especialidad)