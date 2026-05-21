from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.crud.crud_vehiculo import vehiculo as crud_vehiculo
from app.schemas.vehiculo import VehiculoCreate, VehiculoUpdate
from app.models.vehiculo import Vehiculo

class VehiculoService:
    async def create(self, db: AsyncSession, id_persona: int, data: VehiculoCreate) -> Vehiculo:
        # Verificar matrícula única
        existing = await crud_vehiculo.get_by_matricula(db, data.matricula)
        if existing:
            raise HTTPException(status_code=400, detail="Matrícula ya registrada")
        vehiculo_data = data.dict()
        vehiculo_data["id_persona"] = id_persona
        nuevo = await crud_vehiculo.create(db, vehiculo_data)  # Solo flush, sin commit
        await db.commit()
        return nuevo

    async def update(self, db: AsyncSession, vehiculo_id: int, id_persona: int, data: VehiculoUpdate) -> Vehiculo:
        vehiculo = await crud_vehiculo.get(db, vehiculo_id)
        if not vehiculo or vehiculo.id_persona != id_persona:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        update_data = data.dict(exclude_unset=True)
        # Si se actualiza la matrícula, verificar unicidad
        if "matricula" in update_data and update_data["matricula"] != vehiculo.matricula:
            existing = await crud_vehiculo.get_by_matricula(db, update_data["matricula"])
            if existing:
                raise HTTPException(status_code=400, detail="Matrícula ya registrada")
        # Actualizar
        vehiculo = await crud_vehiculo.update(db, vehiculo, update_data)
        await db.commit()
        return vehiculo

    async def delete(self, db: AsyncSession, vehiculo_id: int, id_persona: int) -> None:
        vehiculo = await crud_vehiculo.get(db, vehiculo_id)
        if not vehiculo or vehiculo.id_persona != id_persona:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        await crud_vehiculo.delete(db, vehiculo_id)
        await db.commit()

    async def list_paginated(
        self, db: AsyncSession, id_persona: int, skip: int = 0, limit: int = 10
    ) -> Tuple[List[Vehiculo], int]:
        # Limitar máximo de elementos por página
        limit = min(limit, 100)
        return await crud_vehiculo.get_by_persona_paginated(db, id_persona, skip, limit)

vehiculo_service = VehiculoService()