"""
Endpoints para gestión de servicios desde la perspectiva del taller
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape

from app.db.session import get_db
from app.core.deps import get_current_usuario, require_permiso_en_taller
from app.core.config import settings
from app.models.usuario import Usuario
from app.schemas.servicio import (
    SolicitudServicioListResponse,
    SolicitudServicioDetalleResponse,
    TecnicoDisponibleResponse,
    VehiculoTallerDisponibleResponse,
    ServicioResponse,
    ServicioCreate,
    EvidenciaDetalleResponse,
    VehiculoClienteResponse,
    DiagnosticoDetalleResponse,
    TecnicoAsignadoResponse,
    VehiculoAsignadoResponse
)
from app.services import servicio_service
from app.crud import (
    solicitud_servicio as solicitud_servicio_crud,
    diagnostico as diagnostico_crud,
    solicitud_diagnostico as solicitud_diagnostico_crud,
    vehiculo as vehiculo_crud,
    evidencia as evidencia_crud,
    servicio as servicio_crud,
    servicio_tecnico as servicio_tecnico_crud,
    servicio_vehiculo as servicio_vehiculo_crud,
    empleado as empleado_crud
)
from app.models.vehiculo_taller import VehiculoTaller

router = APIRouter(prefix="/taller", tags=["Taller - Gestión de Servicios"])


@router.get("/solicitudes/recientes", response_model=List[SolicitudServicioListResponse])
async def listar_solicitudes_recientes(
    id_taller: int,
    minutos: int = 60,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista solicitudes de servicio recientes (últimos X minutos) para un taller.
    Solo para administradores del taller.
    """
    solicitudes = await servicio_service.obtener_solicitudes_recientes(db, id_taller, minutos)
    
    # Construir respuesta resumida
    resultado = []
    for solicitud in solicitudes:
        # Verificar si ya tiene servicio creado
        servicio = await servicio_crud.get_by_solicitud(db, solicitud.id)
        tiene_servicio = servicio is not None
        
        resultado.append(SolicitudServicioListResponse(
            id=solicitud.id,
            fecha=solicitud.fecha,
            estado=solicitud.estado.value,
            sugerido_por=solicitud.sugerido_por.value,
            distancia_km=solicitud.distancia_km,
            comentario=solicitud.comentario,
            tiene_servicio=tiene_servicio
        ))
    
    return resultado


@router.get("/solicitudes/historico", response_model=List[SolicitudServicioListResponse])
async def listar_solicitudes_historico(
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas las solicitudes de servicio (historial) para un taller.
    Solo para administradores del taller.
    """
    
    solicitudes = await servicio_service.obtener_solicitudes_historicas(db, id_taller)
    
    resultado = []
    for solicitud in solicitudes:
        servicio = await servicio_crud.get_by_solicitud(db, solicitud.id)
        tiene_servicio = servicio is not None
        
        resultado.append(SolicitudServicioListResponse(
            id=solicitud.id,
            fecha=solicitud.fecha,
            estado=solicitud.estado.value,
            sugerido_por=solicitud.sugerido_por.value,
            distancia_km=solicitud.distancia_km,
            comentario=solicitud.comentario,
            tiene_servicio=tiene_servicio
        ))
    
    return resultado


@router.get("/solicitudes/{solicitud_id}/detalle", response_model=SolicitudServicioDetalleResponse)
async def obtener_detalle_solicitud(
    solicitud_id: int,
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el detalle completo de una solicitud de servicio.
    Incluye: ubicación, diagnóstico, vehículo, evidencias (fotos, audio, transcripción).
    """
    
    solicitud = await solicitud_servicio_crud.get(db, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if solicitud.id_taller != id_taller:
        raise HTTPException(status_code=403, detail="La solicitud no pertenece a este taller")
    
    # Obtener diagnóstico
    diagnostico = await diagnostico_crud.get(db, solicitud.id_diagnostico)
    diagnostico_response = None
    if diagnostico:
        diagnostico_response = DiagnosticoDetalleResponse(
            id=diagnostico.id,
            descripcion=diagnostico.descripcion,
            nivel_confianza=diagnostico.nivel_confianza,
            fecha=diagnostico.fecha
        )
    
    # Obtener solicitud de diagnóstico para ubicación y descripción del conductor
    solicitud_diag = await solicitud_diagnostico_crud.get(db, diagnostico.id_solicitud_diagnostico)
    ubicacion_str = None
    descripcion_conductor = solicitud_diag.descripcion if solicitud_diag else None
    
    if solicitud_diag and solicitud_diag.ubicacion:
        point = to_shape(solicitud_diag.ubicacion)
        ubicacion_str = f"{point.y},{point.x}"
    
    # Obtener vehículo del cliente
    vehiculo_response = None
    if solicitud_diag:
        vehiculo = await vehiculo_crud.get(db, solicitud_diag.id_vehiculo)
        if vehiculo:
            vehiculo_response = VehiculoClienteResponse(
                matricula=vehiculo.matricula,
                marca=vehiculo.marca,
                modelo=vehiculo.modelo,
                anio=vehiculo.anio,
                color=vehiculo.color,
                tipo=vehiculo.tipo
            )
    
    # Obtener evidencias (fotos y audio)
    evidencias_list = []
    if solicitud_diag:
        from sqlalchemy import select
        result = await db.execute(
            select(evidencia_crud.model).where(
                evidencia_crud.model.id_solicitud_diagnostico == solicitud_diag.id
            )
        )
        evidencias = result.scalars().all()
        for evidencia in evidencias:
            # Construir URL completa con BASE_URL
            url_completa = evidencia.url
            if not url_completa.startswith('http'):
                # Si la URL es relativa, agregar BASE_URL
                if url_completa.startswith('/'):
                    url_completa = f"{settings.BASE_URL}{url_completa}"
                else:
                    url_completa = f"{settings.BASE_URL}/{url_completa}"
            
            evidencias_list.append(EvidenciaDetalleResponse(
                id=evidencia.id,
                url=url_completa,
                tipo=evidencia.tipo.value,
                transcripcion=evidencia.transcripcion
            ))
    
    # Construir respuesta completa
    return SolicitudServicioDetalleResponse(
        id=solicitud.id,
        ubicacion=ubicacion_str,
        fecha=solicitud.fecha,
        comentario=solicitud.comentario,
        estado=solicitud.estado.value,
        sugerido_por=solicitud.sugerido_por.value,
        distancia_km=solicitud.distancia_km,
        diagnostico=diagnostico_response,
        vehiculo_cliente=vehiculo_response,
        evidencias=evidencias_list,
        descripcion_conductor=descripcion_conductor
    )


@router.get("/recursos/tecnicos-disponibles", response_model=List[TecnicoDisponibleResponse])
async def listar_tecnicos_disponibles(
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista técnicos disponibles (no en servicio) del taller.
    """
    
    tecnicos_info = await servicio_service.obtener_tecnicos_disponibles(db, id_taller)
    
    return [
        TecnicoDisponibleResponse(
            id=t['id'],
            nombre_completo=t['nombre_completo'],
            especialidades=t['especialidades'],
            estado=t['estado']
        )
        for t in tecnicos_info
    ]


@router.get("/recursos/vehiculos-disponibles", response_model=List[VehiculoTallerDisponibleResponse])
async def listar_vehiculos_disponibles(
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista vehículos disponibles (no en servicio) del taller.
    """
    
    vehiculos = await servicio_service.obtener_vehiculos_disponibles(db, id_taller)
    
    return [
        VehiculoTallerDisponibleResponse(
            id=v.id,
            matricula=v.matricula,
            marca=v.marca,
            modelo=v.modelo,
            tipo=v.tipo,
            estado=v.estado.value
        )
        for v in vehiculos
    ]


@router.post("/solicitudes/{solicitud_id}/aceptar", response_model=ServicioResponse, status_code=status.HTTP_201_CREATED)
async def aceptar_solicitud(
    solicitud_id: int,
    id_taller: int,
    servicio_data: ServicioCreate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Acepta una solicitud de servicio y crea un servicio asignando técnicos y vehículos.
    Cambia el estado de los recursos a "en_servicio".
    """
    
    try:
        servicio = await servicio_service.aceptar_solicitud_servicio(
            db=db,
            id_solicitud=solicitud_id,
            id_taller=id_taller,
            tecnicos_ids=servicio_data.tecnicos_ids,
            vehiculos_ids=servicio_data.vehiculos_ids
        )
        
        # Enviar notificación al cliente
        from app.services.notification_service import notification_service
        try:
            await notification_service.notificar_solicitud_aceptada(db, servicio)
        except Exception as e:
            # Log error pero no fallar la operación principal
            import logging
            logging.getLogger(__name__).error(f"Error enviando notificación: {e}")
        
        # Obtener técnicos asignados
        tecnicos_asignados = await servicio_tecnico_crud.get_by_servicio(db, servicio.id)
        tecnicos_response = []
        for asignacion in tecnicos_asignados:
            empleado = await empleado_crud.get_with_usuario(db, asignacion.id_empleado)
            if empleado:
                tecnicos_response.append(TecnicoAsignadoResponse(
                    id_empleado=empleado.id,
                    nombre_completo=empleado.usuario.nombre
                ))
        
        # Obtener vehículos asignados
        vehiculos_asignados = await servicio_vehiculo_crud.get_by_servicio(db, servicio.id)
        vehiculos_response = []
        for asignacion in vehiculos_asignados:
            from sqlalchemy import select
            result = await db.execute(
                select(VehiculoTaller).where(VehiculoTaller.id == asignacion.id_vehiculo_taller)
            )
            vehiculo = result.scalar_one_or_none()
            if vehiculo:
                vehiculos_response.append(VehiculoAsignadoResponse(
                    id_vehiculo_taller=vehiculo.id,
                    matricula=vehiculo.matricula,
                    marca=vehiculo.marca,
                    modelo=vehiculo.modelo
                ))
        
        return ServicioResponse(
            id=servicio.id,
            fecha=servicio.fecha,
            estado=servicio.estado.value,
            id_taller=servicio.id_taller,
            id_solicitud_servicio=servicio.id_solicitud_servicio,
            tecnicos_asignados=tecnicos_response,
            vehiculos_asignados=vehiculos_response
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/solicitudes/{solicitud_id}/rechazar", status_code=status.HTTP_200_OK)
async def rechazar_solicitud(
    solicitud_id: int,
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Rechaza una solicitud de servicio.
    """
    
    try:
        await servicio_service.rechazar_solicitud_servicio(db, solicitud_id, id_taller)
        return {"message": "Solicitud rechazada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/servicios/en-proceso", response_model=List[ServicioResponse])
async def listar_servicios_en_proceso(
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista servicios activos (creado, en_proceso) del taller.
    """
    
    from app.models.servicio import EstadoServicio
    from sqlalchemy import select, or_
    
    result = await db.execute(
        select(servicio_crud.model).where(
            servicio_crud.model.id_taller == id_taller,
            servicio_crud.model.estado.in_([
                EstadoServicio.creado,
                EstadoServicio.tecnico_asignado,
                EstadoServicio.en_camino,
                EstadoServicio.en_lugar,
                EstadoServicio.en_atencion
            ])
        ).order_by(servicio_crud.model.fecha.desc())
    )
    
    servicios = result.scalars().all()
    
    # Construir respuesta con técnicos y vehículos
    resultado = []
    for servicio in servicios:
        # Técnicos
        tecnicos_asignados = await servicio_tecnico_crud.get_by_servicio(db, servicio.id)
        tecnicos_response = []
        for asignacion in tecnicos_asignados:
            empleado = await empleado_crud.get_with_usuario(db, asignacion.id_empleado)
            if empleado:
                tecnicos_response.append(TecnicoAsignadoResponse(
                    id_empleado=empleado.id,
                    nombre_completo=empleado.usuario.nombre
                ))
        
        # Vehículos
        vehiculos_asignados = await servicio_vehiculo_crud.get_by_servicio(db, servicio.id)
        vehiculos_response = []
        for asignacion in vehiculos_asignados:
            from sqlalchemy import select as sel
            result_v = await db.execute(
                sel(VehiculoTaller).where(VehiculoTaller.id == asignacion.id_vehiculo_taller)
            )
            vehiculo = result_v.scalar_one_or_none()
            if vehiculo:
                vehiculos_response.append(VehiculoAsignadoResponse(
                    id_vehiculo_taller=vehiculo.id,
                    matricula=vehiculo.matricula,
                    marca=vehiculo.marca,
                    modelo=vehiculo.modelo
                ))
        
        resultado.append(ServicioResponse(
            id=servicio.id,
            fecha=servicio.fecha,
            estado=servicio.estado.value,
            id_taller=servicio.id_taller,
            id_solicitud_servicio=servicio.id_solicitud_servicio,
            tecnicos_asignados=tecnicos_response,
            vehiculos_asignados=vehiculos_response
        ))
    
    return resultado


@router.get("/servicios/historico", response_model=List[ServicioResponse])
async def listar_servicios_historico(
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista servicios completados/cancelados del taller.
    """
    
    from app.models.servicio import EstadoServicio
    from sqlalchemy import select, or_
    
    result = await db.execute(
        select(servicio_crud.model).where(
            servicio_crud.model.id_taller == id_taller,
            or_(
                servicio_crud.model.estado == EstadoServicio.finalizado,
                servicio_crud.model.estado == EstadoServicio.cancelado
            )
        ).order_by(servicio_crud.model.fecha.desc())
    )
    
    servicios = result.scalars().all()
    
    resultado = []
    for servicio in servicios:
        tecnicos_asignados = await servicio_tecnico_crud.get_by_servicio(db, servicio.id)
        tecnicos_response = []
        for asignacion in tecnicos_asignados:
            empleado = await empleado_crud.get_with_usuario(db, asignacion.id_empleado)
            if empleado:
                tecnicos_response.append(TecnicoAsignadoResponse(
                    id_empleado=empleado.id,
                    nombre_completo=empleado.usuario.nombre
                ))
        
        vehiculos_asignados = await servicio_vehiculo_crud.get_by_servicio(db, servicio.id)
        vehiculos_response = []
        for asignacion in vehiculos_asignados:
            from sqlalchemy import select as sel
            result_v = await db.execute(
                sel(VehiculoTaller).where(VehiculoTaller.id == asignacion.id_vehiculo_taller)
            )
            vehiculo = result_v.scalar_one_or_none()
            if vehiculo:
                vehiculos_response.append(VehiculoAsignadoResponse(
                    id_vehiculo_taller=vehiculo.id,
                    matricula=vehiculo.matricula,
                    marca=vehiculo.marca,
                    modelo=vehiculo.modelo
                ))
        
        resultado.append(ServicioResponse(
            id=servicio.id,
            fecha=servicio.fecha,
            estado=servicio.estado.value,
            id_taller=servicio.id_taller,
            id_solicitud_servicio=servicio.id_solicitud_servicio,
            tecnicos_asignados=tecnicos_response,
            vehiculos_asignados=vehiculos_response
        ))
    
    return resultado


@router.post("/servicios/{servicio_id}/completar", response_model=ServicioResponse)
async def completar_servicio(
    servicio_id: int,
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Marca un servicio como completado y libera recursos (técnicos y vehículos).
    """
    
    try:
        servicio = await servicio_service.completar_servicio(db, servicio_id, id_taller)
        
        # Obtener técnicos y vehículos
        tecnicos_asignados = await servicio_tecnico_crud.get_by_servicio(db, servicio.id)
        tecnicos_response = []
        for asignacion in tecnicos_asignados:
            empleado = await empleado_crud.get_with_usuario(db, asignacion.id_empleado)
            if empleado:
                tecnicos_response.append(TecnicoAsignadoResponse(
                    id_empleado=empleado.id,
                    nombre_completo=empleado.usuario.nombre
                ))
        
        vehiculos_asignados = await servicio_vehiculo_crud.get_by_servicio(db, servicio.id)
        vehiculos_response = []
        for asignacion in vehiculos_asignados:
            from sqlalchemy import select
            result = await db.execute(
                select(VehiculoTaller).where(VehiculoTaller.id == asignacion.id_vehiculo_taller)
            )
            vehiculo = result.scalar_one_or_none()
            if vehiculo:
                vehiculos_response.append(VehiculoAsignadoResponse(
                    id_vehiculo_taller=vehiculo.id,
                    matricula=vehiculo.matricula,
                    marca=vehiculo.marca,
                    modelo=vehiculo.modelo
                ))
        
        return ServicioResponse(
            id=servicio.id,
            fecha=servicio.fecha,
            estado=servicio.estado.value,
            id_taller=servicio.id_taller,
            id_solicitud_servicio=servicio.id_solicitud_servicio,
            tecnicos_asignados=tecnicos_response,
            vehiculos_asignados=vehiculos_response
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/servicios/{servicio_id}/detalle", response_model=ServicioResponse)
async def obtener_detalle_servicio(
    servicio_id: int,
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el detalle completo de un servicio.
    """
    
    servicio = await servicio_crud.get(db, servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    if servicio.id_taller != id_taller:
        raise HTTPException(status_code=403, detail="El servicio no pertenece a este taller")
    
    # Obtener técnicos y vehículos
    tecnicos_asignados = await servicio_tecnico_crud.get_by_servicio(db, servicio.id)
    tecnicos_response = []
    for asignacion in tecnicos_asignados:
        empleado = await empleado_crud.get_with_usuario(db, asignacion.id_empleado)
        if empleado:
            tecnicos_response.append(TecnicoAsignadoResponse(
                id_empleado=empleado.id,
                nombre_completo=empleado.usuario.nombre
            ))
    
    vehiculos_asignados = await servicio_vehiculo_crud.get_by_servicio(db, servicio.id)
    vehiculos_response = []
    for asignacion in vehiculos_asignados:
        from sqlalchemy import select
        result = await db.execute(
            select(VehiculoTaller).where(VehiculoTaller.id == asignacion.id_vehiculo_taller)
        )
        vehiculo = result.scalar_one_or_none()
        if vehiculo:
            vehiculos_response.append(VehiculoAsignadoResponse(
                id_vehiculo_taller=vehiculo.id,
                matricula=vehiculo.matricula,
                marca=vehiculo.marca,
                modelo=vehiculo.modelo
            ))
    
    return ServicioResponse(
        id=servicio.id,
        fecha=servicio.fecha,
        estado=servicio.estado.value,
        id_taller=servicio.id_taller,
        id_solicitud_servicio=servicio.id_solicitud_servicio,
        tecnicos_asignados=tecnicos_response,
        vehiculos_asignados=vehiculos_response
    )


# ============================================================================
# ENDPOINTS PARA MÉTRICAS E HISTORIAL
# ============================================================================

from pydantic import BaseModel
from datetime import timedelta
from typing import Optional

class EstadoHistorialResponse(BaseModel):
    estado: str
    estado_descripcion: str
    tiempo: str  # ISO format
    
class MetricaResponse(BaseModel):
    tiempo_respuesta: Optional[str]  # formato legible ej: "5 minutos"
    tiempo_respuesta_segundos: Optional[int]
    tiempo_llegada: Optional[str]
    tiempo_llegada_segundos: Optional[int]
    tiempo_resolucion: Optional[str]
    tiempo_resolucion_segundos: Optional[int]
    tiempo_total: Optional[str]
    tiempo_total_segundos: Optional[int]


def format_timedelta(td: timedelta) -> str:
    """Convierte un timedelta a formato legible"""
    if not td:
        return None
    
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


def get_estado_descripcion(estado: str) -> str:
    """Retorna la descripción en español del estado"""
    map_estados = {
        'creado': 'Creado',
        'tecnico_asignado': 'Técnico Asignado',
        'en_camino': 'En Camino',
        'en_lugar': 'En el Lugar',
        'en_atencion': 'En Atención',
        'finalizado': 'Finalizado',
        'cancelado': 'Cancelado'
    }
    return map_estados.get(estado, estado)


@router.get("/servicios/{servicio_id}/historial", response_model=List[EstadoHistorialResponse])
async def obtener_historial_estados(
    servicio_id: int,
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el historial completo de cambios de estado de un servicio.
    Útil para seguimiento en tiempo real de servicios en proceso.
    """
    from sqlalchemy import select
    from app.models.historial_estado_servicio import HistorialEstadoServicio
    from app.models.servicio import Servicio
    
    # Verificar que el servicio existe y pertenece al taller
    servicio = await servicio_crud.get(db, servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    if servicio.id_taller != id_taller:
        raise HTTPException(status_code=403, detail="El servicio no pertenece a este taller")
    
    # Obtener historial ordenado por tiempo
    result = await db.execute(
        select(HistorialEstadoServicio).where(
            HistorialEstadoServicio.id_servicio == servicio_id
        ).order_by(HistorialEstadoServicio.tiempo.asc())
    )
    
    historial = result.scalars().all()
    
    return [
        EstadoHistorialResponse(
            estado=h.estado.value,
            estado_descripcion=get_estado_descripcion(h.estado.value),
            tiempo=h.tiempo.isoformat()
        )
        for h in historial
    ]


@router.get("/servicios/{servicio_id}/metricas", response_model=MetricaResponse)
async def obtener_metricas_servicio(
    servicio_id: int,
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene las métricas calculadas de un servicio finalizado.
    Incluye tiempos de respuesta, llegada y resolución.
    """
    from sqlalchemy import select
    from app.models.metrica import Metrica
    from app.models.servicio import Servicio
    
    # Verificar que el servicio existe y pertenece al taller
    servicio = await servicio_crud.get(db, servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    if servicio.id_taller != id_taller:
        raise HTTPException(status_code=403, detail="El servicio no pertenece a este taller")
    
    # Obtener métricas
    result = await db.execute(
        select(Metrica).where(Metrica.id_servicio == servicio_id)
    )
    
    metrica = result.scalar_one_or_none()
    
    if not metrica:
        raise HTTPException(
            status_code=404, 
            detail="No hay métricas disponibles para este servicio. Las métricas se calculan cuando el servicio se finaliza."
        )
    
    # Calcular tiempo total
    tiempo_total = None
    tiempo_total_segundos = None
    if metrica.tiempo_respuesta and metrica.tiempo_llegada and metrica.tiempo_resolucion:
        tiempo_total = metrica.tiempo_respuesta + metrica.tiempo_llegada + metrica.tiempo_resolucion
        tiempo_total_segundos = int(tiempo_total.total_seconds())
    
    return MetricaResponse(
        tiempo_respuesta=format_timedelta(metrica.tiempo_respuesta) if metrica.tiempo_respuesta else None,
        tiempo_respuesta_segundos=int(metrica.tiempo_respuesta.total_seconds()) if metrica.tiempo_respuesta else None,
        tiempo_llegada=format_timedelta(metrica.tiempo_llegada) if metrica.tiempo_llegada else None,
        tiempo_llegada_segundos=int(metrica.tiempo_llegada.total_seconds()) if metrica.tiempo_llegada else None,
        tiempo_resolucion=format_timedelta(metrica.tiempo_resolucion) if metrica.tiempo_resolucion else None,
        tiempo_resolucion_segundos=int(metrica.tiempo_resolucion.total_seconds()) if metrica.tiempo_resolucion else None,
        tiempo_total=format_timedelta(tiempo_total) if tiempo_total else None,
        tiempo_total_segundos=tiempo_total_segundos
    )


# ============================================================
# ENDPOINT PARA VALORACIONES
# ============================================================

@router.get("/servicios/{servicio_id}/valoracion")
async def obtener_valoracion_servicio_taller(
    servicio_id: int,
    id_taller: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene la valoración de un servicio del taller.
    Permite al taller ver las valoraciones que reciben sus servicios.
    """
    from app.crud import crud_valoracion
    from sqlalchemy import select
    from app.models.servicio import Servicio
    
    # Verificar que el servicio pertenece al taller
    result = await db.execute(
        select(Servicio).where(
            Servicio.id == servicio_id,
            Servicio.id_taller == id_taller
        )
    )
    servicio = result.scalar_one_or_none()
    
    if not servicio:
        raise HTTPException(
            status_code=404,
            detail="Servicio no encontrado o no pertenece a este taller"
        )
    
    # Obtener valoración
    valoracion = await crud_valoracion.valoracion.get_by_servicio(db, servicio_id)
    
    if not valoracion:
        return None
    
    return {
        "id": valoracion.id,
        "puntos": valoracion.puntos,
        "comentario": valoracion.comentario,
        "id_servicio": valoracion.id_servicio
    }
