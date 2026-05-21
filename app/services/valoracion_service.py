"""
Servicio para gestionar valoraciones y actualizar puntos de talleres
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.valoracion import Valoracion
from app.models.servicio import Servicio
from app.models.taller import Taller
from app.crud import crud_valoracion

logger = logging.getLogger(__name__)


async def calcular_y_actualizar_puntos_taller(
    db: AsyncSession,
    id_taller: int
) -> float:
    """
    Calcula el promedio de todas las valoraciones de servicios del taller
    y actualiza el campo 'puntos' del taller.
    
    Returns:
        float: El nuevo promedio de puntos del taller
    """
    # Obtener todas las valoraciones de servicios del taller
    result = await db.execute(
        select(func.avg(Valoracion.puntos)).select_from(Valoracion).join(
            Servicio, Valoracion.id_servicio == Servicio.id
        ).where(
            Servicio.id_taller == id_taller
        )
    )
    
    promedio = result.scalar()
    
    # Si no hay valoraciones, el promedio es 0
    if promedio is None:
        promedio = 0.0
    else:
        # Redondear a 2 decimales
        promedio = round(float(promedio), 2)
    
    # Actualizar el taller
    taller_result = await db.execute(
        select(Taller).where(Taller.id == id_taller)
    )
    taller = taller_result.scalar_one_or_none()
    
    if taller:
        taller.puntos = promedio
        await db.flush()
        logger.info(f"✅ Puntos del taller {id_taller} actualizados a {promedio}")
    else:
        logger.warning(f"⚠️ Taller {id_taller} no encontrado")
    
    return promedio


async def crear_valoracion_y_actualizar_taller(
    db: AsyncSession,
    id_servicio: int,
    puntos: int,
    comentario: str = None
) -> Valoracion:
    """
    Crea una valoración y actualiza automáticamente los puntos del taller.
    """
    # Obtener el servicio para saber a qué taller pertenece
    result = await db.execute(
        select(Servicio).where(Servicio.id == id_servicio)
    )
    servicio = result.scalar_one_or_none()
    
    if not servicio:
        raise ValueError("Servicio no encontrado")
    
    # Crear la valoración
    valoracion = await crud_valoracion.valoracion.crear_valoracion(
        db=db,
        id_servicio=id_servicio,
        puntos=puntos,
        comentario=comentario
    )
    
    # Actualizar puntos del taller
    await calcular_y_actualizar_puntos_taller(db, servicio.id_taller)
    
    return valoracion


async def actualizar_valoracion_y_taller(
    db: AsyncSession,
    valoracion: Valoracion,
    nuevos_puntos: int,
    nuevo_comentario: str = None
) -> Valoracion:
    """
    Actualiza una valoración existente y recalcula los puntos del taller.
    """
    # Obtener el servicio para saber a qué taller pertenece
    result = await db.execute(
        select(Servicio).where(Servicio.id == valoracion.id_servicio)
    )
    servicio = result.scalar_one_or_none()
    
    if not servicio:
        raise ValueError("Servicio no encontrado")
    
    # Actualizar la valoración
    valoracion.puntos = nuevos_puntos
    if nuevo_comentario is not None:
        valoracion.comentario = nuevo_comentario
    
    await db.flush()
    
    # Recalcular puntos del taller
    await calcular_y_actualizar_puntos_taller(db, servicio.id_taller)
    
    return valoracion
