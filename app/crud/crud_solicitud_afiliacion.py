from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.solicitud_afiliacion import SolicitudAfiliacion

class CRUDSolicitudAfiliacion(CRUDBase[SolicitudAfiliacion]):
    async def get_by_usuario_paginated(
        self, db: AsyncSession, id_usuario: int, skip: int = 0, limit: int = 10
    ) -> Tuple[List[SolicitudAfiliacion], int]:
        # Total
        total_result = await db.execute(
            select(func.count()).select_from(SolicitudAfiliacion).where(SolicitudAfiliacion.id_usuario_solicita == id_usuario)
        )
        total = total_result.scalar_one()
        # Items
        result = await db.execute(
            select(SolicitudAfiliacion)
            .where(SolicitudAfiliacion.id_usuario_solicita == id_usuario)
            .order_by(SolicitudAfiliacion.fecha.desc())
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()
        return items, total

    async def get_all_paginated(
        self, db: AsyncSession, skip: int = 0, limit: int = 10
    ) -> Tuple[List[SolicitudAfiliacion], int]:
        total_result = await db.execute(select(func.count()).select_from(SolicitudAfiliacion))
        total = total_result.scalar_one()
        result = await db.execute(
            select(SolicitudAfiliacion)
            .order_by(SolicitudAfiliacion.fecha.desc())
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()
        return items, total

    async def update_estado(self, db: AsyncSession, id: int, estado: str, id_usuario_revisa: int, comentario_revision: Optional[str] = None) -> Optional[SolicitudAfiliacion]:
        solicitud = await self.get(db, id)
        if solicitud:
            solicitud.estado = estado
            solicitud.fecha_revision = func.now()
            solicitud.id_usuario_revisa = id_usuario_revisa
            if comentario_revision is not None:
                solicitud.comentario_revision = comentario_revision
            await db.flush()
            await db.refresh(solicitud)
        return solicitud

solicitud_afiliacion = CRUDSolicitudAfiliacion(SolicitudAfiliacion)