from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.crud.base import CRUDBase
from app.models.sesion import Sesion

class CRUDSesion(CRUDBase[Sesion]):
    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[Sesion]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Sesion).where(
                Sesion.token == token,
                Sesion.activa == True,
                Sesion.fecha_expira > now
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_persona(self, db: AsyncSession, id_persona: int) -> Optional[Sesion]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Sesion).where(
                Sesion.id_persona == id_persona,
                Sesion.activa == True,
                Sesion.fecha_expira > now
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_all_for_persona(self, db: AsyncSession, id_persona: int) -> None:
        await db.execute(
            update(Sesion).where(Sesion.id_persona == id_persona).values(activa=False)
        )

    async def create_session(self, db: AsyncSession, token: str, expires_at: datetime, id_persona: int) -> Sesion:
        return await self.create(db, {
            "token": token,
            "fecha_expira": expires_at,
            "id_persona": id_persona,
            "activa": True
        })

sesion = CRUDSesion(Sesion)