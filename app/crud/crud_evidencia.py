from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.evidencia import Evidencia


class CRUDEvidencia(CRUDBase[Evidencia]):
    """CRUD mínimo para Evidencia"""
    pass


evidencia = CRUDEvidencia(Evidencia)
