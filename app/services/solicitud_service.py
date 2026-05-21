import logging
from typing import Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape
from sqlalchemy import select
from shapely.geometry import Point
from app.crud.crud_solicitud_afiliacion import solicitud_afiliacion
from app.crud.crud_taller import taller as crud_taller
from app.crud.crud_rol import rol as crud_rol
from app.crud.crud_rol_usuario import rol_usuario as crud_rol_usuario
from app.schemas.solicitud import SolicitudAfiliacionCreate, SolicitudAfiliacionResponse, EstadoSolicitudEnum
from app.models.solicitud_afiliacion import SolicitudAfiliacion
from app.models.taller import Taller, EstadoTaller
from app.core.exceptions import RoleNotFoundError
from app.core.config import settings

logger = logging.getLogger(__name__)

def _format_ubicacion(geog) -> str:
    if geog is None:
        return ""
    point = to_shape(geog)
    return f"{point.y},{point.x}"

async def _get_nombre_usuario(db: AsyncSession, id_usuario: int) -> str:
    from app.crud.crud_usuario import usuario as crud_usuario
    user = await crud_usuario.get(db, id_usuario)
    return user.nombre if user else "Desconocido"

async def create_solicitud(db: AsyncSession, id_usuario_solicita: int, data: SolicitudAfiliacionCreate) -> SolicitudAfiliacionResponse:
    # Validar que no exista un taller con el mismo nombre (aprobado)
    existing_taller = await crud_taller.get_by_nombre(db, data.nombre)
    if existing_taller:
        raise HTTPException(status_code=400, detail="Ya existe un taller con ese nombre")
    # Convertir ubicación
    try:
        lat, lon = map(float, data.ubicacion.split(','))
        point = Point(lon, lat)
        from geoalchemy2.shape import from_shape
        ubicacion_geog = from_shape(point, srid=4326)
    except:
        raise HTTPException(status_code=400, detail="Ubicación inválida. Use formato 'lat,lon'")
    # Crear solicitud
    solicitud_data = data.dict(exclude={"ubicacion"})
    solicitud_data["ubicacion"] = ubicacion_geog
    solicitud_data["id_usuario_solicita"] = id_usuario_solicita
    solicitud = await solicitud_afiliacion.create(db, solicitud_data)
    await db.commit()
    # Construir respuesta
    return SolicitudAfiliacionResponse(
        id=solicitud.id,
        nombre=solicitud.nombre,
        ubicacion=_format_ubicacion(solicitud.ubicacion),
        telefono=solicitud.telefono,
        email=solicitud.email,
        comentario=solicitud.comentario,
        fecha=solicitud.fecha,
        fecha_revision=solicitud.fecha_revision,
        estado=solicitud.estado,
        id_usuario_solicita=solicitud.id_usuario_solicita,
        id_usuario_revisa=solicitud.id_usuario_revisa,
        nombre_usuario_solicita=await _get_nombre_usuario(db, solicitud.id_usuario_solicita),
        nombre_usuario_revisa=await _get_nombre_usuario(db, solicitud.id_usuario_revisa) if solicitud.id_usuario_revisa else None,
    )

async def list_mis_solicitudes(db: AsyncSession, id_usuario: int, skip: int, limit: int) -> Tuple[list[SolicitudAfiliacionResponse], int]:
    items, total = await solicitud_afiliacion.get_by_usuario_paginated(db, id_usuario, skip, limit)
    responses = []
    for s in items:
        responses.append(SolicitudAfiliacionResponse(
            id=s.id,
            nombre=s.nombre,
            ubicacion=_format_ubicacion(s.ubicacion),
            telefono=s.telefono,
            email=s.email,
            comentario=s.comentario,
            fecha=s.fecha,
            fecha_revision=s.fecha_revision,
            estado=s.estado,
            comentario_revision=s.comentario_revision,
            id_usuario_solicita=s.id_usuario_solicita,
            id_usuario_revisa=s.id_usuario_revisa,
            nombre_usuario_solicita=await _get_nombre_usuario(db, s.id_usuario_solicita),
            nombre_usuario_revisa=await _get_nombre_usuario(db, s.id_usuario_revisa) if s.id_usuario_revisa else None,
        ))
    return responses, total

async def list_all_solicitudes(db: AsyncSession, skip: int, limit: int) -> Tuple[list[SolicitudAfiliacionResponse], int]:
    items, total = await solicitud_afiliacion.get_all_paginated(db, skip, limit)
    responses = []
    for s in items:
        responses.append(SolicitudAfiliacionResponse(
            id=s.id,
            nombre=s.nombre,
            ubicacion=_format_ubicacion(s.ubicacion),
            telefono=s.telefono,
            email=s.email,
            comentario=s.comentario,
            fecha=s.fecha,
            fecha_revision=s.fecha_revision,
            estado=s.estado,
            comentario_revision=s.comentario_revision,
            id_usuario_solicita=s.id_usuario_solicita,
            id_usuario_revisa=s.id_usuario_revisa,
            nombre_usuario_solicita=await _get_nombre_usuario(db, s.id_usuario_solicita),
            nombre_usuario_revisa=await _get_nombre_usuario(db, s.id_usuario_revisa) if s.id_usuario_revisa else None,
        ))
    return responses, total

async def update_solicitud_estado(
    db: AsyncSession,
    solicitud_id: int,
    estado: EstadoSolicitudEnum,
    id_usuario_revisa: int,
    comentario_revision: Optional[str] = None
) -> SolicitudAfiliacionResponse:
    solicitud = await solicitud_afiliacion.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud.estado != EstadoSolicitudEnum.pendiente:
        raise HTTPException(status_code=400, detail="La solicitud ya fue procesada")
    # Actualizar estado
    solicitud = await solicitud_afiliacion.update_estado(db, solicitud_id, estado, id_usuario_revisa, comentario_revision)
    # Si es aprobada, crear taller y asignar rol super_admin_taller
    if estado == EstadoSolicitudEnum.aprobada:
        # Verificar si ya existe un taller con el mismo nombre
        existing_taller = await crud_taller.get_by_nombre(db, solicitud.nombre)
        if existing_taller:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un taller con el nombre '{solicitud.nombre}'"
            )
        # Crear taller
        taller_data = {
            "nombre": solicitud.nombre,
            "ubicacion": solicitud.ubicacion,
            "telefono": solicitud.telefono,
            "email": solicitud.email,
            "estado": EstadoTaller.activo,
            "id_solicitud_afiliacion": solicitud.id
        }
        nuevo_taller = await crud_taller.create(db, taller_data)
        # Asignar rol super_admin_taller al solicitante
        rol_super_admin = await crud_rol.get_by_nombre(db, "super_admin_taller")
        if not rol_super_admin:
            raise RoleNotFoundError("super_admin_taller")
        # Verificar que no tenga ya ese rol en ese taller
        from app.models.rol_usuario import RolUsuario
        existing = await db.execute(select(RolUsuario).where(
            RolUsuario.id_usuario == solicitud.id_usuario_solicita,
            RolUsuario.id_rol == rol_super_admin.id,
            RolUsuario.id_taller == nuevo_taller.id
        ))
        if not existing.scalar_one_or_none():
            await crud_rol_usuario.add_rol(db, solicitud.id_usuario_solicita, rol_super_admin.id, id_taller=nuevo_taller.id)
    await db.commit()
    # Devolver respuesta actualizada
    return SolicitudAfiliacionResponse(
        id=solicitud.id,
        nombre=solicitud.nombre,
        ubicacion=_format_ubicacion(solicitud.ubicacion),
        telefono=solicitud.telefono,
        email=solicitud.email,
        comentario=solicitud.comentario,
        fecha=solicitud.fecha,
        fecha_revision=solicitud.fecha_revision,
        estado=solicitud.estado,
        comentario_revision=solicitud.comentario_revision,
        id_usuario_solicita=solicitud.id_usuario_solicita,
        id_usuario_revisa=solicitud.id_usuario_revisa,
        nombre_usuario_solicita=await _get_nombre_usuario(db, solicitud.id_usuario_solicita),
        nombre_usuario_revisa=await _get_nombre_usuario(db, solicitud.id_usuario_revisa) if solicitud.id_usuario_revisa else None,
    )

async def list_solicitudes_pendientes(
    db: AsyncSession, skip: int = 0, limit: int = 10
) -> Tuple[list[SolicitudAfiliacionResponse], int]:
    # Obtener solo solicitudes con estado 'pendiente'
    from sqlalchemy import select, func
    from app.models.solicitud_afiliacion import SolicitudAfiliacion
    total_result = await db.execute(
        select(func.count()).select_from(SolicitudAfiliacion).where(SolicitudAfiliacion.estado == "pendiente")
    )
    total = total_result.scalar_one()
    result = await db.execute(
        select(SolicitudAfiliacion)
        .where(SolicitudAfiliacion.estado == "pendiente")
        .order_by(SolicitudAfiliacion.fecha.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    responses = []
    for s in items:
        responses.append(SolicitudAfiliacionResponse(
            id=s.id,
            nombre=s.nombre,
            ubicacion=_format_ubicacion(s.ubicacion),
            telefono=s.telefono,
            email=s.email,
            comentario=s.comentario,
            fecha=s.fecha,
            fecha_revision=s.fecha_revision,
            estado=s.estado,
            id_usuario_solicita=s.id_usuario_solicita,
            id_usuario_revisa=s.id_usuario_revisa,
            nombre_usuario_solicita=await _get_nombre_usuario(db, s.id_usuario_solicita),
            nombre_usuario_revisa=await _get_nombre_usuario(db, s.id_usuario_revisa) if s.id_usuario_revisa else None,
            comentario_revision=s.comentario_revision,
        ))
    return responses, total