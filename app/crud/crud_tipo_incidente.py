from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.tipo_incidente import TipoIncidente


class CRUDTipoIncidente(CRUDBase[TipoIncidente]):
    async def get_by_concepto(self, db: AsyncSession, concepto: str) -> Optional[TipoIncidente]:
        result = await db.execute(select(TipoIncidente).where(TipoIncidente.concepto == concepto))
        return result.scalar_one_or_none()
    
    async def get_all(self, db: AsyncSession) -> List[TipoIncidente]:
        """Obtiene todos los tipos de incidentes"""
        result = await db.execute(select(TipoIncidente).order_by(TipoIncidente.concepto))
        return list(result.scalars().all())


tipo_incidente = CRUDTipoIncidente(TipoIncidente)
