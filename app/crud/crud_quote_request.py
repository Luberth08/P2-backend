from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.crud.base import CRUDBase
from app.models.quote_request import QuoteRequest, EstadoQuoteRequest
from datetime import datetime, timedelta


class CRUDQuoteRequest(CRUDBase[QuoteRequest]):
    async def get_by_cliente(
        self,
        db: AsyncSession,
        id_cliente: int,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[EstadoQuoteRequest] = None
    ) -> Tuple[List[QuoteRequest], int]:
        """Obtiene las solicitudes de cotización de un cliente"""
        query = select(QuoteRequest).where(QuoteRequest.id_cliente == id_cliente)
        
        if estado:
            query = query.where(QuoteRequest.estado == estado)
        
        # Contar total
        count_query = select(QuoteRequest.id).where(QuoteRequest.id_cliente == id_cliente)
        if estado:
            count_query = count_query.where(QuoteRequest.estado == estado)
        
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        query = query.order_by(QuoteRequest.fecha_creacion.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().all())
        
        return items, total
    
    async def get_by_taller(
        self,
        db: AsyncSession,
        id_taller: int,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[EstadoQuoteRequest] = None
    ) -> Tuple[List[QuoteRequest], int]:
        """Obtiene las solicitudes de cotización para un taller"""
        from app.models.quote_response import QuoteResponse
        
        # Unir con quote_response para filtrar por taller
        query = select(QuoteRequest).join(
            QuoteResponse,
            QuoteRequest.id == QuoteResponse.id_quote_request
        ).where(QuoteResponse.id_taller == id_taller)
        
        if estado:
            query = query.where(QuoteRequest.estado == estado)
        
        # Contar total
        count_query = select(QuoteRequest.id).join(
            QuoteResponse,
            QuoteRequest.id == QuoteResponse.id_quote_request
        ).where(QuoteResponse.id_taller == id_taller)
        
        if estado:
            count_query = count_query.where(QuoteRequest.estado == estado)
        
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        query = query.order_by(QuoteRequest.fecha_creacion.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().unique().all())
        
        return items, total
    
    async def get_pending_for_taller(
        self,
        db: AsyncSession,
        id_taller: int,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[QuoteRequest], int]:
        """Obtiene las solicitudes pendientes que un taller aún no ha respondido"""
        from app.models.quote_response import QuoteResponse
        
        # Subquery para obtener IDs de solicitudes que el taller ya respondió
        subquery = select(QuoteResponse.id_quote_request).where(
            QuoteResponse.id_taller == id_taller
        )
        
        # Obtener solicitudes pendientes donde el taller tiene una QuoteResponse pero aún no respondió
        query = select(QuoteRequest).join(
            QuoteResponse,
            QuoteRequest.id == QuoteResponse.id_quote_request
        ).where(
            and_(
                QuoteResponse.id_taller == id_taller,
                QuoteRequest.estado == EstadoQuoteRequest.pendiente,
                QuoteResponse.estado == "pendiente"
            )
        )
        
        # Contar total
        count_query = select(QuoteRequest.id).join(
            QuoteResponse,
            QuoteRequest.id == QuoteResponse.id_quote_request
        ).where(
            and_(
                QuoteResponse.id_taller == id_taller,
                QuoteRequest.estado == EstadoQuoteRequest.pendiente,
                QuoteResponse.estado == "pendiente"
            )
        )
        
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        query = query.order_by(QuoteRequest.fecha_creacion.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().unique().all())
        
        return items, total
    
    async def update_estado(
        self,
        db: AsyncSession,
        request_id: int,
        nuevo_estado: EstadoQuoteRequest
    ) -> Optional[QuoteRequest]:
        """Actualiza el estado de una solicitud de cotización"""
        request = await self.get(db, request_id)
        if not request:
            return None
        
        request.estado = nuevo_estado
        
        if nuevo_estado == EstadoQuoteRequest.aceptada:
            request.fecha_aceptada = datetime.utcnow()
        
        await db.flush()
        return request
    
    async def mark_expired(self, db: AsyncSession) -> List[QuoteRequest]:
        """Marca como expiradas las solicitudes que pasaron el tiempo límite (1 hora)"""
        from app.models.quote_response import QuoteResponse, EstadoQuoteResponse
        
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        # Obtener solicitudes pendientes que expiraron
        result = await db.execute(
            select(QuoteRequest).where(
                and_(
                    QuoteRequest.estado == EstadoQuoteRequest.pendiente,
                    QuoteRequest.fecha_creacion < one_hour_ago
                )
            )
        )
        expired_requests = list(result.scalars().all())
        
        # Marcar solicitudes como expiradas
        for request in expired_requests:
            request.estado = EstadoQuoteRequest.expirada
            
            # También marcar las respuestas pendientes como expiradas
            responses_result = await db.execute(
                select(QuoteResponse).where(
                    and_(
                        QuoteResponse.id_quote_request == request.id,
                        QuoteResponse.estado == EstadoQuoteResponse.pendiente
                    )
                )
            )
            responses = list(responses_result.scalars().all())
            
            for response in responses:
                response.estado = EstadoQuoteResponse.expirada
        
        await db.flush()
        return expired_requests


quote_request = CRUDQuoteRequest(QuoteRequest)
