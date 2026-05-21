from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.vehiculo import VehiculoCreate, VehiculoUpdate, VehiculoResponse, VehiculoListResponse
from app.services.vehiculo_service import vehiculo_service
from app.core.deps import get_current_persona
from app.models.persona import Persona
from app.crud.crud_vehiculo import vehiculo as crud_vehiculo

router = APIRouter(tags=["Vehículos"])

@router.get("/", response_model=VehiculoListResponse)
async def list_vehiculos(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(10, ge=1, le=100, description="Cantidad de registros por página"),
    current_persona: Persona = Depends(get_current_persona),
    db: AsyncSession = Depends(get_db)
):
    items, total = await vehiculo_service.list_paginated(db, current_persona.id, skip, limit)
    return VehiculoListResponse(items=items, total=total, skip=skip, limit=limit)

@router.get("/{vehiculo_id}", response_model=VehiculoResponse)
async def get_vehiculo(
    vehiculo_id: int,
    current_persona: Persona = Depends(get_current_persona),
    db: AsyncSession = Depends(get_db)
):
    vehiculo = await crud_vehiculo.get(db, vehiculo_id)
    if not vehiculo or vehiculo.id_persona != current_persona.id:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return vehiculo

@router.post("/", response_model=VehiculoResponse, status_code=status.HTTP_201_CREATED)
async def create_vehiculo(
    req: VehiculoCreate,
    current_persona: Persona = Depends(get_current_persona),
    db: AsyncSession = Depends(get_db)
):
    return await vehiculo_service.create(db, current_persona.id, req)

@router.put("/{vehiculo_id}", response_model=VehiculoResponse)
async def update_vehiculo(
    vehiculo_id: int,
    req: VehiculoUpdate,
    current_persona: Persona = Depends(get_current_persona),
    db: AsyncSession = Depends(get_db)
):
    return await vehiculo_service.update(db, vehiculo_id, current_persona.id, req)

@router.delete("/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehiculo(
    vehiculo_id: int,
    current_persona: Persona = Depends(get_current_persona),
    db: AsyncSession = Depends(get_db)
):
    await vehiculo_service.delete(db, vehiculo_id, current_persona.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)