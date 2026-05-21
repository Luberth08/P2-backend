from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.requiere_especialidad import RequiereEspecialidad


class CRUDRequiereEspecialidad:
    def __init__(self):
        self.model = RequiereEspecialidad

    async def get_especialidades_by_categoria(
        self, db: AsyncSession, id_categoria: int
    ) -> List[int]:
        """Obtiene los IDs de especialidades requeridas por una categoría"""
        result = await db.execute(
            select(RequiereEspecialidad.id_especialidad).where(
                RequiereEspecialidad.id_categoria_incidente == id_categoria
            )
        )
        return list(result.scalars().all())

    async def get_categorias_by_especialidad(
        self, db: AsyncSession, id_especialidad: int
    ) -> List[int]:
        """Obtiene los IDs de categorías que requieren una especialidad"""
        result = await db.execute(
            select(RequiereEspecialidad.id_categoria_incidente).where(
                RequiereEspecialidad.id_especialidad == id_especialidad
            )
        )
        return list(result.scalars().all())

    async def add_especialidad_to_categoria(
        self, db: AsyncSession, id_categoria: int, id_especialidad: int
    ) -> RequiereEspecialidad:
        """Asocia una especialidad a una categoría"""
        obj = RequiereEspecialidad(
            id_categoria_incidente=id_categoria,
            id_especialidad=id_especialidad
        )
        db.add(obj)
        await db.flush()
        return obj

    async def remove_especialidad_from_categoria(
        self, db: AsyncSession, id_categoria: int, id_especialidad: int
    ) -> None:
        """Elimina la asociación entre una especialidad y una categoría"""
        await db.execute(
            delete(RequiereEspecialidad).where(
                RequiereEspecialidad.id_categoria_incidente == id_categoria,
                RequiereEspecialidad.id_especialidad == id_especialidad
            )
        )
        await db.flush()

    async def remove_all_especialidades_from_categoria(
        self, db: AsyncSession, id_categoria: int
    ) -> None:
        """Elimina todas las especialidades asociadas a una categoría"""
        await db.execute(
            delete(RequiereEspecialidad).where(
                RequiereEspecialidad.id_categoria_incidente == id_categoria
            )
        )
        await db.flush()

    async def set_especialidades_for_categoria(
        self, db: AsyncSession, id_categoria: int, especialidad_ids: List[int]
    ) -> None:
        """Reemplaza todas las especialidades de una categoría con una nueva lista"""
        # Eliminar todas las asociaciones existentes
        await self.remove_all_especialidades_from_categoria(db, id_categoria)
        
        # Agregar las nuevas asociaciones
        for id_especialidad in especialidad_ids:
            await self.add_especialidad_to_categoria(db, id_categoria, id_especialidad)


requiere_especialidad = CRUDRequiereEspecialidad()
