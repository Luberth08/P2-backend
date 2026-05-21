from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.rol import Rol

class CRUDRol(CRUDBase[Rol]):
    async def get_by_nombre(self, db: AsyncSession, nombre: str) -> Optional[Rol]:
        result = await db.execute(select(Rol).where(Rol.nombre == nombre))
        return result.scalar_one_or_none()

rol = CRUDRol(Rol)