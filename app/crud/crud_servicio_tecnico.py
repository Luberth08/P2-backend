from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.crud.base import CRUDBase
from app.models.servicio_tecnico import ServicioTecnico


class CRUDServicioTecnico(CRUDBase[ServicioTecnico]):
    async def get_by_servicio(
        self,
        db: AsyncSession,
        id_servicio: int
    ) -> List[ServicioTecnico]:
        """Obtiene todos los técnicos asignados a un servicio"""
        result = await db.execute(
            select(ServicioTecnico).where(
                ServicioTecnico.id_servicio == id_servicio
            )
        )
        return list(result.scalars().all())
    
    async def delete_by_servicio(
        self,
        db: AsyncSession,
        id_servicio: int
    ):
        """Elimina todas las asignaciones de técnicos de un servicio"""
        await db.execute(
            delete(ServicioTecnico).where(
                ServicioTecnico.id_servicio == id_servicio
            )
        )


servicio_tecnico = CRUDServicioTecnico(ServicioTecnico)
