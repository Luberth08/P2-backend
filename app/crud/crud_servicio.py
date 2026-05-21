from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from app.crud.base import CRUDBase
from app.models.servicio import Servicio, EstadoServicio


class CRUDServicio(CRUDBase[Servicio]):
    async def get_by_taller(
        self,
        db: AsyncSession,
        id_taller: int,
        estado: Optional[EstadoServicio] = None
    ) -> List[Servicio]:
        """Obtiene servicios de un taller, opcionalmente filtrados por estado"""
        query = select(Servicio).where(Servicio.id_taller == id_taller)
        
        if estado:
            query = query.where(Servicio.estado == estado)
        
        query = query.order_by(Servicio.fecha.desc())
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_en_proceso(
        self,
        db: AsyncSession,
        id_taller: int
    ) -> List[Servicio]:
        """Obtiene servicios en proceso de un taller (todos los estados activos)"""
        result = await db.execute(
            select(Servicio).where(
                and_(
                    Servicio.id_taller == id_taller,
                    or_(
                        Servicio.estado == EstadoServicio.creado,
                        Servicio.estado == EstadoServicio.tecnico_asignado,
                        Servicio.estado == EstadoServicio.en_camino,
                        Servicio.estado == EstadoServicio.en_lugar,
                        Servicio.estado == EstadoServicio.en_atencion
                    )
                )
            ).order_by(Servicio.fecha.desc())
        )
        return list(result.scalars().all())
    
    async def get_historicos(
        self,
        db: AsyncSession,
        id_taller: int
    ) -> List[Servicio]:
        """Obtiene servicios completados o cancelados de un taller"""
        result = await db.execute(
            select(Servicio).where(
                and_(
                    Servicio.id_taller == id_taller,
                    or_(
                        Servicio.estado == EstadoServicio.finalizado,
                        Servicio.estado == EstadoServicio.cancelado
                    )
                )
            ).order_by(Servicio.fecha.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_solicitud(
        self,
        db: AsyncSession,
        id_solicitud_servicio: int
    ) -> Optional[Servicio]:
        """Obtiene un servicio por su solicitud de servicio"""
        result = await db.execute(
            select(Servicio).where(
                Servicio.id_solicitud_servicio == id_solicitud_servicio
            )
        )
        return result.scalar_one_or_none()
    
    async def update_estado(
        self,
        db: AsyncSession,
        servicio_id: int,
        nuevo_estado: EstadoServicio
    ) -> Optional[Servicio]:
        """Actualiza el estado de un servicio"""
        servicio = await self.get(db, servicio_id)
        if not servicio:
            return None
        
        servicio.estado = nuevo_estado
        await db.flush()
        return servicio


servicio = CRUDServicio(Servicio)
