from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.crud.base import CRUDBase
from app.models.persona import Persona

class CRUDPersona(CRUDBase[Persona]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Persona]:
        result = await db.execute(select(Persona).where(Persona.email == email))
        return result.scalar_one_or_none()

    async def get_by_ci_complemento(
        self, db: AsyncSession, ci: str, complemento: Optional[str] = None
    ) -> Optional[Persona]:
        # Si complemento es cadena vacía, tratarlo como None
        comp_val = complemento if complemento else None
        if comp_val is None:
            condition = and_(Persona.ci == ci, Persona.complemento.is_(None))
        else:
            condition = and_(Persona.ci == ci, Persona.complemento == comp_val)
        result = await db.execute(select(Persona).where(condition))
        return result.scalar_one_or_none()

persona = CRUDPersona(Persona)