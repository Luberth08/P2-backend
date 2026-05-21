from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.rol_permiso import RolPermiso
from app.models.permiso import Permiso
from app.models.rol import Rol
from app.models.rol_usuario import RolUsuario
from app.crud.base import CRUDBase

class CRUDRolPermiso(CRUDBase[RolPermiso]):
    async def get_permisos_by_rol(self, db: AsyncSession, id_rol: int) -> List[RolPermiso]:
        result = await db.execute(select(RolPermiso).where(RolPermiso.id_rol == id_rol))
        return result.scalars().all()

    async def add_permiso(self, db: AsyncSession, id_rol: int, id_permiso: int) -> RolPermiso:
        nuevo = RolPermiso(id_rol=id_rol, id_permiso=id_permiso)
        db.add(nuevo)
        await db.flush()
        await db.refresh(nuevo)
        return nuevo

    async def remove_permiso(self, db: AsyncSession, id_rol: int, id_permiso: int) -> None:
        await db.execute(
            delete(RolPermiso).where(
                RolPermiso.id_rol == id_rol,
                RolPermiso.id_permiso == id_permiso
            )
        )
        await db.flush()

    async def get_permisos_conceptos_by_usuario(self, db: AsyncSession, id_usuario: int) -> List[str]:
        """
        Obtiene la lista de conceptos de permisos que tiene un usuario a través de sus roles.
        """
        stmt = select(Permiso.concepto).join(
            RolPermiso, Permiso.id == RolPermiso.id_permiso
        ).join(
            Rol, Rol.id == RolPermiso.id_rol
        ).join(
            RolUsuario, Rol.id == RolUsuario.id_rol
        ).where(
            RolUsuario.id_usuario == id_usuario
        )
        result = await db.execute(stmt)
        return result.scalars().all()

rol_permiso = CRUDRolPermiso(RolPermiso)