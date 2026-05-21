from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.valoracion import Valoracion


class CRUDValoracion(CRUDBase[Valoracion]):
    
    async def get_by_servicio(
        self,
        db: AsyncSession,
        id_servicio: int
    ) -> Optional[Valoracion]:
        """Obtiene la valoración de un servicio"""
        result = await db.execute(
            select(Valoracion).where(Valoracion.id_servicio == id_servicio)
        )
        return result.scalar_one_or_none()
    
    async def crear_valoracion(
        self,
        db: AsyncSession,
        id_servicio: int,
        puntos: int,
        comentario: Optional[str] = None
    ) -> Valoracion:
        """
        Crea una valoración para un servicio.
        Solo se puede valorar una vez por servicio (unique constraint).
        """
        valoracion = Valoracion(
            id_servicio=id_servicio,
            puntos=puntos,
            comentario=comentario
        )
        db.add(valoracion)
        await db.flush()
        return valoracion


valoracion = CRUDValoracion(Valoracion)
