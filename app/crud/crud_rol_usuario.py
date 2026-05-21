from typing import List, Optional
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.rol_usuario import RolUsuario

class CRUDRolUsuario:
    async def get_roles_by_usuario(self, db: AsyncSession, id_usuario: int) -> List[RolUsuario]:
        """Obtiene todas las relaciones rol-usuario para un usuario dado."""
        result = await db.execute(
            select(RolUsuario)
            .where(RolUsuario.id_usuario == id_usuario)
            .options(selectinload(RolUsuario.rol))
        )
        return result.scalars().all()

    async def add_rol(self, db: AsyncSession, id_usuario: int, id_rol: int, id_taller: Optional[int] = None) -> RolUsuario:
        """Asigna un rol a un usuario (opcionalmente en un taller específico)."""
        nuevo = RolUsuario(id_usuario=id_usuario, id_rol=id_rol, id_taller=id_taller)
        db.add(nuevo)
        await db.flush()
        await db.refresh(nuevo)
        return nuevo

    async def remove_rol(self, db: AsyncSession, id_usuario: int, id_rol: int, id_taller: Optional[int] = None) -> None:
        """Elimina la asignación de un rol a un usuario (y taller si se especifica)."""
        condiciones = [
            RolUsuario.id_usuario == id_usuario,
            RolUsuario.id_rol == id_rol
        ]
        if id_taller is not None:
            condiciones.append(RolUsuario.id_taller == id_taller)
        await db.execute(
            delete(RolUsuario).where(*condiciones)
        )
        await db.flush()

    async def user_has_rol(self, db: AsyncSession, id_usuario: int, id_rol: int, id_taller: Optional[int] = None) -> bool:
        """Verifica si un usuario tiene un rol específico (opcionalmente en un taller)."""
        condiciones = [
            RolUsuario.id_usuario == id_usuario,
            RolUsuario.id_rol == id_rol
        ]
        if id_taller is not None:
            condiciones.append(RolUsuario.id_taller == id_taller)
        result = await db.execute(
            select(RolUsuario).where(*condiciones)
        )
        return result.scalar_one_or_none() is not None

rol_usuario = CRUDRolUsuario()