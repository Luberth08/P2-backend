from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.incidente import Incidente


class CRUDIncidente(CRUDBase[Incidente]):
    """CRUD para `Incidente`."""
    
    async def get_by_diagnostico_and_tipo(
        self,
        db: AsyncSession,
        id_diagnostico: int,
        id_tipo_incidente: int
    ) -> Optional[Incidente]:
        """Busca un incidente por diagnóstico y tipo de incidente"""
        result = await db.execute(
            select(Incidente).where(
                Incidente.id_diagnostico == id_diagnostico,
                Incidente.id_tipo_incidente == id_tipo_incidente
            )
        )
        return result.scalar_one_or_none()


incidente = CRUDIncidente(Incidente)
