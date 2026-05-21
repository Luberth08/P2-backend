from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.usuario import Usuario

class CRUDUsuario(CRUDBase[Usuario]):
    async def get_by_id_persona(self, db: AsyncSession, id_persona: int) -> Optional[Usuario]:
        result = await db.execute(select(Usuario).where(Usuario.id_persona == id_persona))
        return result.scalar_one_or_none()
    
    async def get_by_nombre(self, db: AsyncSession, nombre: str) -> Optional[Usuario]:
        result = await db.execute(select(Usuario).where(Usuario.nombre == nombre))
        return result.scalar_one_or_none()

usuario = CRUDUsuario(Usuario)