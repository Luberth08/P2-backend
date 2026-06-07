from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.crud.base import CRUDBase
from app.models.quote_response import QuoteResponse, EstadoQuoteResponse
from decimal import Decimal


class CRUDQuoteResponse(CRUDBase[QuoteResponse]):
    async def get_by_quote_request(
        self,
        db: AsyncSession,
        id_quote_request: int
    ) -> List[QuoteResponse]:
        """Obtiene todas las respuestas para una solicitud de cotización"""
        result = await db.execute(
            select(QuoteResponse)
            .where(QuoteResponse.id_quote_request == id_quote_request)
            .order_by(QuoteResponse.fecha_creacion.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_taller(
        self,
        db: AsyncSession,
        id_taller: int,
        estado: Optional[EstadoQuoteResponse] = None
    ) -> List[QuoteResponse]:
        """Obtiene todas las respuestas de cotización de un taller"""
        query = select(QuoteResponse).where(QuoteResponse.id_taller == id_taller)
        
        if estado:
            query = query.where(QuoteResponse.estado == estado)
        
        query = query.order_by(QuoteResponse.fecha_creacion.desc())
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_taller_and_request(
        self,
        db: AsyncSession,
        id_taller: int,
        id_quote_request: int
    ) -> Optional[QuoteResponse]:
        """Obtiene la respuesta de un taller a una solicitud específica"""
        result = await db.execute(
            select(QuoteResponse).where(
                and_(
                    QuoteResponse.id_taller == id_taller,
                    QuoteResponse.id_quote_request == id_quote_request
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_with_items(
        self,
        db: AsyncSession,
        id_quote_request: int,
        id_taller: int,
        items_data: List[dict]
    ) -> QuoteResponse:
        """Crea una respuesta de cotización con sus items"""
        from app.models.quote_item import QuoteItem
        from datetime import datetime
        
        # Calcular total
        total = sum(Decimal(str(item['precio'])) for item in items_data)
        
        # Crear respuesta
        response = QuoteResponse(
            id_quote_request=id_quote_request,
            id_taller=id_taller,
            estado=EstadoQuoteResponse.respondida,
            fecha_respuesta=datetime.utcnow(),
            total=total
        )
        
        db.add(response)
        await db.flush()
        
        # Crear items
        for item_data in items_data:
            item = QuoteItem(
                id_quote_response=response.id,
                titulo=item_data['titulo'],
                precio=Decimal(str(item_data['precio']))
            )
            db.add(item)
        
        await db.flush()
        
        # Actualizar estado de la solicitud a "con_respuesta"
        from app.crud.crud_quote_request import quote_request
        from app.models.quote_request import EstadoQuoteRequest
        quote_req = await quote_request.get(db, id_quote_request)
        if quote_req and quote_req.estado == EstadoQuoteRequest.pendiente:
            quote_req.estado = EstadoQuoteRequest.con_respuesta
        
        await db.flush()
        return response
    
    async def update_estado(
        self,
        db: AsyncSession,
        response_id: int,
        nuevo_estado: EstadoQuoteResponse
    ) -> Optional[QuoteResponse]:
        """Actualiza el estado de una respuesta de cotización"""
        response = await self.get(db, response_id)
        if not response:
            return None
        
        response.estado = nuevo_estado
        await db.flush()
        return response
    
    async def mark_others_as_rejected(
        self,
        db: AsyncSession,
        accepted_response_id: int,
        id_quote_request: int
    ) -> List[QuoteResponse]:
        """Marca las otras respuestas como rechazadas cuando una es aceptada"""
        result = await db.execute(
            select(QuoteResponse).where(
                and_(
                    QuoteResponse.id_quote_request == id_quote_request,
                    QuoteResponse.id != accepted_response_id
                )
            )
        )
        other_responses = list(result.scalars().all())
        
        for response in other_responses:
            response.estado = EstadoQuoteResponse.rechazada
        
        await db.flush()
        return other_responses


quote_response = CRUDQuoteResponse(QuoteResponse)
