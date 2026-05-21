from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.diagnostico import Diagnostico


class CRUDDiagnostico(CRUDBase[Diagnostico]):
    async def get_by_solicitud(self, db: AsyncSession, id_solicitud: int) -> Optional[Diagnostico]:
        result = await db.execute(select(Diagnostico).where(Diagnostico.id_solicitud_diagnostico == id_solicitud))
        return result.scalar_one_or_none()


diagnostico = CRUDDiagnostico(Diagnostico)
