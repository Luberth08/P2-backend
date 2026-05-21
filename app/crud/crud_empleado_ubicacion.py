from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from app.crud.base import CRUDBase
from app.models.empleado_ubicacion import EmpleadoUbicacion


class CRUDEmpleadoUbicacion(CRUDBase[EmpleadoUbicacion]):
    
    async def get_ubicacion_activa(
        self,
        db: AsyncSession,
        id_empleado: int
    ) -> Optional[EmpleadoUbicacion]:
        """Obtiene la ubicación activa de un empleado"""
        result = await db.execute(
            select(EmpleadoUbicacion).where(
                and_(
                    EmpleadoUbicacion.id_empleado == id_empleado,
                    EmpleadoUbicacion.activa == True
                )
            ).order_by(EmpleadoUbicacion.timestamp.desc())
        )
        return result.scalar_one_or_none()
    
    async def get_ubicaciones_activas_servicio(
        self,
        db: AsyncSession,
        id_servicio: int
    ) -> List[EmpleadoUbicacion]:
        """Obtiene todas las ubicaciones activas de técnicos de un servicio"""
        result = await db.execute(
            select(EmpleadoUbicacion).where(
                and_(
                    EmpleadoUbicacion.id_servicio == id_servicio,
                    EmpleadoUbicacion.activa == True
                )
            ).order_by(EmpleadoUbicacion.timestamp.desc())
        )
        return result.scalars().all()
    
    async def desactivar_ubicaciones_empleado(
        self,
        db: AsyncSession,
        id_empleado: int
    ) -> None:
        """Desactiva todas las ubicaciones activas de un empleado"""
        await db.execute(
            update(EmpleadoUbicacion).where(
                and_(
                    EmpleadoUbicacion.id_empleado == id_empleado,
                    EmpleadoUbicacion.activa == True
                )
            ).values(activa=False)
        )
        await db.flush()
    
    async def crear_ubicacion(
        self,
        db: AsyncSession,
        id_empleado: int,
        latitud: float,
        longitud: float,
        id_servicio: Optional[int] = None
    ) -> EmpleadoUbicacion:
        """
        Crea una nueva ubicación para un empleado.
        Desactiva automáticamente las ubicaciones anteriores.
        """
        # Desactivar ubicaciones anteriores
        await self.desactivar_ubicaciones_empleado(db, id_empleado)
        
        # Crear nueva ubicación activa
        ubicacion = EmpleadoUbicacion(
            id_empleado=id_empleado,
            latitud=latitud,
            longitud=longitud,
            activa=True,
            id_servicio=id_servicio
        )
        db.add(ubicacion)
        await db.flush()
        
        return ubicacion


empleado_ubicacion = CRUDEmpleadoUbicacion(EmpleadoUbicacion)
