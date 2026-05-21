from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.dispositivo_usuario import DispositivoUsuario

class CRUDDispositivoUsuario(CRUDBase[DispositivoUsuario]):
    async def get_by_persona(self, db: AsyncSession, id_persona: int) -> List[DispositivoUsuario]:
        result = await db.execute(select(DispositivoUsuario).where(DispositivoUsuario.id_persona == id_persona))
        return result.scalars().all()

    async def get_by_token(self, db: AsyncSession, token_fcm: str) -> Optional[DispositivoUsuario]:
        result = await db.execute(select(DispositivoUsuario).where(DispositivoUsuario.token_fcm == token_fcm))
        return result.scalar_one_or_none()

    async def delete_by_token(self, db: AsyncSession, token_fcm: str) -> None:
        dispositivo = await self.get_by_token(db, token_fcm)
        if dispositivo:
            await self.delete(db, dispositivo.id)

dispositivo_usuario = CRUDDispositivoUsuario(DispositivoUsuario)