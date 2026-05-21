from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from app.models.tecnico_especialidad import TecnicoEspecialidad

class CRUDTecnicoEspecialidad:
    async def add(self, db: AsyncSession, id_empleado: int, id_especialidad: int):
        nuevo = TecnicoEspecialidad(id_empleado=id_empleado, id_especialidad=id_especialidad)
        db.add(nuevo)
        await db.flush()
        return nuevo

    async def remove_all_for_empleado(self, db: AsyncSession, id_empleado: int):
        await db.execute(delete(TecnicoEspecialidad).where(TecnicoEspecialidad.id_empleado == id_empleado))
        await db.flush()

    async def get_by_empleado(self, db: AsyncSession, id_empleado: int):
        result = await db.execute(select(TecnicoEspecialidad).where(TecnicoEspecialidad.id_empleado == id_empleado))
        return result.scalars().all()

    async def get_by_especialidad(self, db: AsyncSession, id_especialidad: int):
        result = await db.execute(select(TecnicoEspecialidad).where(TecnicoEspecialidad.id_especialidad == id_especialidad))
        return result.scalars().all()

tecnico_especialidad = CRUDTecnicoEspecialidad()