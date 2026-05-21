from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.crud.base import CRUDBase
from app.models.servicio_vehiculo import ServicioVehiculo


class CRUDServicioVehiculo(CRUDBase[ServicioVehiculo]):
    async def get_by_servicio(
        self,
        db: AsyncSession,
        id_servicio: int
    ) -> List[ServicioVehiculo]:
        """Obtiene todos los vehículos asignados a un servicio"""
        result = await db.execute(
            select(ServicioVehiculo).where(
                ServicioVehiculo.id_servicio == id_servicio
            )
        )
        return list(result.scalars().all())
    
    async def delete_by_servicio(
        self,
        db: AsyncSession,
        id_servicio: int
    ):
        """Elimina todas las asignaciones de vehículos de un servicio"""
        await db.execute(
            delete(ServicioVehiculo).where(
                ServicioVehiculo.id_servicio == id_servicio
            )
        )


servicio_vehiculo = CRUDServicioVehiculo(ServicioVehiculo)
