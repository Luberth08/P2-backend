from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.categoria_incidente import CategoriaIncidente


class CRUDCategoriaIncidente(CRUDBase[CategoriaIncidente]):
    async def get_by_nombre(self, db: AsyncSession, nombre: str) -> Optional[CategoriaIncidente]:
        result = await db.execute(select(CategoriaIncidente).where(CategoriaIncidente.nombre == nombre))
        return result.scalar_one_or_none()


categoria_incidente = CRUDCategoriaIncidente(CategoriaIncidente)
