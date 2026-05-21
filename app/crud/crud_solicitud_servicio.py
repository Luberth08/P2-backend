from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.crud.base import CRUDBase
from app.models.solicitud_servicio import SolicitudServicio, EstadoSolicitudServicio


class CRUDSolicitudServicio(CRUDBase[SolicitudServicio]):
    async def get_by_diagnostico(
        self, 
        db: AsyncSession, 
        id_diagnostico: int
    ) -> List[SolicitudServicio]:
        """Obtiene todas las solicitudes de servicio para un diagnóstico"""
        result = await db.execute(
            select(SolicitudServicio)
            .where(SolicitudServicio.id_diagnostico == id_diagnostico)
            .order_by(SolicitudServicio.fecha.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_taller(
        self, 
        db: AsyncSession, 
        id_taller: int,
        estado: Optional[EstadoSolicitudServicio] = None
    ) -> List[SolicitudServicio]:
        """Obtiene todas las solicitudes de servicio para un taller"""
        query = select(SolicitudServicio).where(SolicitudServicio.id_taller == id_taller)
        
        if estado:
            query = query.where(SolicitudServicio.estado == estado)
        
        query = query.order_by(SolicitudServicio.fecha.desc())
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_taller_and_diagnostico(
        self,
        db: AsyncSession,
        id_taller: int,
        id_diagnostico: int
    ) -> Optional[SolicitudServicio]:
        """Verifica si ya existe una solicitud para este taller y diagnóstico"""
        result = await db.execute(
            select(SolicitudServicio).where(
                and_(
                    SolicitudServicio.id_taller == id_taller,
                    SolicitudServicio.id_diagnostico == id_diagnostico
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_estado(
        self,
        db: AsyncSession,
        solicitud_id: int,
        nuevo_estado: EstadoSolicitudServicio,
        costo_estimado: Optional[float] = None
    ) -> Optional[SolicitudServicio]:
        """Actualiza el estado de una solicitud de servicio"""
        solicitud = await self.get(db, solicitud_id)
        if not solicitud:
            return None
        
        solicitud.estado = nuevo_estado
        
        if nuevo_estado == EstadoSolicitudServicio.aceptada:
            from datetime import datetime
            solicitud.fecha_aceptada = datetime.utcnow()
            if costo_estimado is not None:
                solicitud.costo_estimado = costo_estimado
        
        await db.flush()
        return solicitud


solicitud_servicio = CRUDSolicitudServicio(SolicitudServicio)
