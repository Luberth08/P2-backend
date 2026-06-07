from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.quote_item import QuoteItem


class CRUDQuoteItem(CRUDBase[QuoteItem]):
    async def get_by_quote_response(
        self,
        db: AsyncSession,
        id_quote_response: int
    ) -> List[QuoteItem]:
        """Obtiene todos los items de una respuesta de cotización"""
        result = await db.execute(
            select(QuoteItem)
            .where(QuoteItem.id_quote_response == id_quote_response)
            .order_by(QuoteItem.id)
        )
        return list(result.scalars().all())


quote_item = CRUDQuoteItem(QuoteItem)
