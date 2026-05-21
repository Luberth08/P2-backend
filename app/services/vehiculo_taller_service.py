import logging
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.crud.crud_vehiculo_taller import vehiculo_taller as crud_vehiculo_taller
from app.schemas.vehiculo_taller import VehiculoTallerCreate, VehiculoTallerUpdate
from app.models.vehiculo_taller import EstadoVehiculoTaller, VehiculoTaller

logger = logging.getLogger(__name__)

class VehiculoTallerService:
    async def create(self, db: AsyncSession, id_taller: int, data: VehiculoTallerCreate, id_usuario_actual: int) -> VehiculoTaller:
        existing = await crud_vehiculo_taller.get_by_matricula(db, data.matricula)
        if existing:
            raise HTTPException(status_code=400, detail="Matrícula ya registrada")
        obj = data.dict()
        obj["id_taller"] = id_taller
        obj["estado"] = EstadoVehiculoTaller.disponible
        nuevo = await crud_vehiculo_taller.create(db, obj)
        await db.commit()
        return nuevo

    async def list_by_taller(self, db: AsyncSession, id_taller: int, estado: Optional[str], skip: int, limit: int) -> Tuple[List[VehiculoTaller], int]:
        estado_enum = None
        if estado:
            try:
                estado_enum = EstadoVehiculoTaller(estado)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Estado inválido: {estado}")
        return await crud_vehiculo_taller.get_by_taller(db, id_taller, estado_enum, skip, limit)

    async def update(self, db: AsyncSession, id_taller: int, vehiculo_id: int, data: VehiculoTallerUpdate, id_usuario_actual: int) -> VehiculoTaller:
        veh = await crud_vehiculo_taller.get(db, vehiculo_id)
        if not veh or veh.id_taller != id_taller:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado en este taller")
        update_data = data.dict(exclude_unset=True)
        if "matricula" in update_data and update_data["matricula"] != veh.matricula:
            existing = await crud_vehiculo_taller.get_by_matricula(db, update_data["matricula"])
            if existing:
                raise HTTPException(status_code=400, detail="Matrícula ya registrada")
        veh = await crud_vehiculo_taller.update(db, veh, update_data)
        await db.commit()
        return veh

    async def set_inactive(self, db: AsyncSession, id_taller: int, vehiculo_id: int, id_usuario_actual: int) -> VehiculoTaller:
        veh = await crud_vehiculo_taller.get(db, vehiculo_id)
        if not veh or veh.id_taller != id_taller:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado en este taller")
        veh.estado = EstadoVehiculoTaller.inactivo
        veh = await crud_vehiculo_taller.update(db, veh, {"estado": EstadoVehiculoTaller.inactivo})
        await db.commit()
        return veh


vehiculo_taller_service = VehiculoTallerService()
