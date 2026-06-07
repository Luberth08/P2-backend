from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.solicitud_servicio import SolicitudServicio, EstadoSolicitudServicio
from app.models.servicio import Servicio, EstadoServicio
from app.models.historial_estado_servicio import HistorialEstadoServicio
from app.models.incidente import Incidente
from app.models.tipo_incidente import TipoIncidente
from app.models.diagnostico import Diagnostico
from app.models.taller import Taller
from app.schemas.kpi import (
    DashboardKPIs,
    TiempoPromedioKPI,
    IncidentePorTipoKPI,
    TallerEficienteKPI,
    ZonaIncidenteKPI,
    CasosCanceladosKPI,
    SLAKPI
)


class KPIService:
    
    @staticmethod
    async def get_dashboard_kpis(
        db: AsyncSession,
        taller_id: int,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> DashboardKPIs:
        """Obtiene todos los KPIs del dashboard para un taller específico"""
        
        # Si no se proporcionan fechas, usar los últimos 30 días
        if not fecha_fin:
            fecha_fin = datetime.utcnow()
        if not fecha_inicio:
            fecha_inicio = fecha_fin - timedelta(days=30)
        
        # Asegurar que las fechas sean offset-naive (sin timezone) para compatibilidad con PostgreSQL
        if fecha_inicio.tzinfo is not None:
            fecha_inicio = fecha_inicio.replace(tzinfo=None)
        if fecha_fin.tzinfo is not None:
            fecha_fin = fecha_fin.replace(tzinfo=None)
        
        # Calcular cada KPI
        tiempo_promedio = await KPIService._calcular_tiempo_promedio(db, taller_id, fecha_inicio, fecha_fin)
        incidentes_por_tipo = await KPIService._calcular_incidentes_por_tipo(db, taller_id, fecha_inicio, fecha_fin)
        talleres_eficientes = await KPIService._calcular_talleres_eficientes(db, taller_id, fecha_inicio, fecha_fin)
        zonas_incidentes = await KPIService._calcular_zonas_incidentes(db, taller_id, fecha_inicio, fecha_fin)
        casos_cancelados = await KPIService._calcular_casos_cancelados(db, taller_id, fecha_inicio, fecha_fin)
        cumplimiento_sla = await KPIService._calcular_cumplimiento_sla(db, taller_id, fecha_inicio, fecha_fin)
        
        # Obtener nombre del taller
        result = await db.execute(select(Taller.nombre).where(Taller.id == taller_id))
        taller_nombre = result.scalar() or f"Taller {taller_id}"
        
        return DashboardKPIs(
            taller_id=taller_id,
            nombre=taller_nombre,
            periodo_inicio=fecha_inicio,
            periodo_fin=fecha_fin,
            tiempo_promedio=tiempo_promedio,
            incidentes_por_tipo=incidentes_por_tipo,
            talleres_eficientes=talleres_eficientes,
            zonas_incidentes=zonas_incidentes,
            casos_cancelados=casos_cancelados,
            cumplimiento_sla=cumplimiento_sla
        )
    
    @staticmethod
    async def _calcular_tiempo_promedio(
        db: AsyncSession,
        taller_id: int,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> TiempoPromedioKPI:
        """Calcula el tiempo promedio de asignación y llegada"""
        
        # Tiempo de asignación: entre fecha de solicitud y fecha_aceptada
        query_asignacion = select(
            func.avg(
                func.extract('epoch', SolicitudServicio.fecha_aceptada) - 
                func.extract('epoch', SolicitudServicio.fecha)
            ) / 60  # Convertir a minutos
        ).where(
            and_(
                SolicitudServicio.id_taller == taller_id,
                SolicitudServicio.fecha >= fecha_inicio,
                SolicitudServicio.fecha <= fecha_fin,
                SolicitudServicio.fecha_aceptada.isnot(None),
                SolicitudServicio.estado == EstadoSolicitudServicio.aceptada
            )
        )
        
        result_asignacion = await db.execute(query_asignacion)
        tiempo_asignacion = result_asignacion.scalar() or 0.0
        
        # Tiempo de llegada: entre fecha_aceptada y primer estado "en_lugar" del servicio
        # Primero obtenemos los servicios aceptados en el periodo
        query_servicios = select(Servicio).where(
            and_(
                Servicio.id_taller == taller_id,
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin
            )
        ).options(
            selectinload(Servicio.historial_estados),
            selectinload(Servicio.solicitud_servicio)
        )
        
        result_servicios = await db.execute(query_servicios)
        servicios = result_servicios.scalars().all()
        
        tiempos_llegada = []
        for servicio in servicios:
            # Buscar el primer historial con estado "en_lugar"
            historial_en_lugar = None
            for hist in servicio.historial_estados:
                if hist.estado == EstadoServicio.en_lugar:
                    historial_en_lugar = hist
                    break
            
            if historial_en_lugar and servicio.solicitud_servicio and servicio.solicitud_servicio.fecha_aceptada:
                fecha_aceptada = servicio.solicitud_servicio.fecha_aceptada
                if fecha_aceptada.tzinfo is not None:
                    fecha_aceptada = fecha_aceptada.replace(tzinfo=None)
                tiempo_lugar = historial_en_lugar.tiempo
                if tiempo_lugar.tzinfo is not None:
                    tiempo_lugar = tiempo_lugar.replace(tzinfo=None)
                tiempo = (tiempo_lugar - fecha_aceptada).total_seconds() / 60
                tiempos_llegada.append(tiempo)
        
        tiempo_llegada = sum(tiempos_llegada) / len(tiempos_llegada) if tiempos_llegada else 0.0
        
        return TiempoPromedioKPI(
            tiempo_asignacion_minutos=round(tiempo_asignacion, 2),
            tiempo_llegada_minutos=round(tiempo_llegada, 2)
        )
    
    @staticmethod
    async def _calcular_incidentes_por_tipo(
        db: AsyncSession,
        taller_id: int,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> List[IncidentePorTipoKPI]:
        """Calcula la distribución de incidentes por tipo"""
        
        # Obtener incidentes del taller en el periodo
        query = select(
            TipoIncidente.concepto,
            func.count(Incidente.id_tipo_incidente).label('cantidad')
        ).join(
            Diagnostico, Incidente.id_diagnostico == Diagnostico.id
        ).join(
            SolicitudServicio, Diagnostico.id == SolicitudServicio.id_diagnostico
        ).join(
            TipoIncidente, Incidente.id_tipo_incidente == TipoIncidente.id
        ).where(
            and_(
                SolicitudServicio.id_taller == taller_id,
                SolicitudServicio.fecha >= fecha_inicio,
                SolicitudServicio.fecha <= fecha_fin
            )
        ).group_by(TipoIncidente.concepto)
        
        result = await db.execute(query)
        rows = result.all()
        
        total = sum(row.cantidad for row in rows)
        
        kpis = []
        for row in rows:
            porcentaje = (row.cantidad / total * 100) if total > 0 else 0.0
            kpis.append(IncidentePorTipoKPI(
                tipo=row.concepto,
                cantidad=row.cantidad,
                porcentaje=round(porcentaje, 2)
            ))
        
        # Ordenar por cantidad descendente
        kpis.sort(key=lambda x: x.cantidad, reverse=True)
        
        return kpis
    
    @staticmethod
    async def _calcular_talleres_eficientes(
        db: AsyncSession,
        taller_id: int,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> List[TallerEficienteKPI]:
        """Calcula los talleres más eficientes (comparado con otros talleres)"""
        
        # Para un taller específico, mostramos su eficiencia comparada
        # Obtener todos los talleres con servicios en el periodo
        query = select(
            Taller.id,
            Taller.nombre,
            func.count(Servicio.id).label('total_servicios')
        ).join(
            Servicio, Taller.id == Servicio.id_taller
        ).where(
            and_(
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin
            )
        ).group_by(Taller.id, Taller.nombre)
        
        result = await db.execute(query)
        talleres_data = result.all()
        
        kpis = []
        for taller_id_item, nombre, total_servicios in talleres_data:
            # Calcular tiempo de respuesta promedio para este taller
            query_tiempo = select(
                func.avg(
                    func.extract('epoch', HistorialEstadoServicio.tiempo) - 
                    func.extract('epoch', Servicio.fecha)
                ) / 60
            ).join(
                Servicio, HistorialEstadoServicio.id_servicio == Servicio.id
            ).where(
                and_(
                    Servicio.id_taller == taller_id_item,
                    Servicio.fecha >= fecha_inicio,
                    Servicio.fecha <= fecha_fin,
                    HistorialEstadoServicio.estado == EstadoServicio.en_lugar
                )
            )
            
            result_tiempo = await db.execute(query_tiempo)
            tiempo_respuesta = result_tiempo.scalar() or 0.0
            
            # Calcular tiempo de finalización promedio
            query_finalizacion = select(
                func.avg(
                    func.extract('epoch', HistorialEstadoServicio.tiempo) - 
                    func.extract('epoch', Servicio.fecha)
                ) / 60
            ).join(
                Servicio, HistorialEstadoServicio.id_servicio == Servicio.id
            ).where(
                and_(
                    Servicio.id_taller == taller_id_item,
                    Servicio.fecha >= fecha_inicio,
                    Servicio.fecha <= fecha_fin,
                    HistorialEstadoServicio.estado == EstadoServicio.finalizado
                )
            )
            
            result_finalizacion = await db.execute(query_finalizacion)
            tiempo_finalizacion = result_finalizacion.scalar() or 0.0
            
            kpis.append(TallerEficienteKPI(
                taller_id=taller_id_item,
                nombre=nombre,
                tiempo_respuesta_promedio_minutos=round(tiempo_respuesta, 2),
                tiempo_finalizacion_promedio_minutos=round(tiempo_finalizacion, 2),
                total_servicios=total_servicios
            ))
        
        # Ordenar por tiempo de respuesta (menor es mejor)
        kpis.sort(key=lambda x: x.tiempo_respuesta_promedio_minutos)
        
        return kpis[:10]  # Retornar top 10
    
    @staticmethod
    async def _calcular_zonas_incidentes(
        db: AsyncSession,
        taller_id: int,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> List[ZonaIncidenteKPI]:
        """Calcula las zonas con más incidentes (agrupando por áreas geográficas)"""
        
        # Obtener ubicaciones de las solicitudes del taller
        # Convertir geography a geometry para poder usar ST_X y ST_Y
        query = select(
            func.ST_X(func.ST_GeomFromText(func.ST_AsText(SolicitudServicio.ubicacion))).label('longitud'),
            func.ST_Y(func.ST_GeomFromText(func.ST_AsText(SolicitudServicio.ubicacion))).label('latitud')
        ).where(
            and_(
                SolicitudServicio.id_taller == taller_id,
                SolicitudServicio.fecha >= fecha_inicio,
                SolicitudServicio.fecha <= fecha_fin,
                SolicitudServicio.ubicacion.isnot(None)
            )
        )
        
        result = await db.execute(query)
        ubicaciones = result.all()
        
        # Agrupar en zonas (cuadrícula de 0.01 grados ~ 1km)
        zonas: Dict[str, Dict] = {}
        for lat, lon in ubicaciones:
            if lat is None or lon is None:
                continue
            
            # Redondear a 2 decimales para crear zonas
            zona_key = f"{round(lat, 2)},{round(lon, 2)}"
            
            if zona_key not in zonas:
                zonas[zona_key] = {
                    'lat_sum': lat,
                    'lon_sum': lon,
                    'count': 0
                }
            
            zonas[zona_key]['count'] += 1
        
        # Convertir a KPIs
        kpis = []
        for zona_key, data in zonas.items():
            kpis.append(ZonaIncidenteKPI(
                zona=zona_key,
                latitud_promedio=round(data['lat_sum'], 4),
                longitud_promedio=round(data['lon_sum'], 4),
                cantidad_incidentes=data['count']
            ))
        
        # Ordenar por cantidad de incidentes
        kpis.sort(key=lambda x: x.cantidad_incidentes, reverse=True)
        
        return kpis[:10]  # Retornar top 10 zonas
    
    @staticmethod
    async def _calcular_casos_cancelados(
        db: AsyncSession,
        taller_id: int,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> CasosCanceladosKPI:
        """Calcula los casos cancelados"""
        
        # Total de servicios
        query_total = select(func.count(Servicio.id)).where(
            and_(
                Servicio.id_taller == taller_id,
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin
            )
        )
        
        result_total = await db.execute(query_total)
        total_servicios = result_total.scalar() or 0
        
        # Total cancelados
        query_cancelados = select(func.count(Servicio.id)).where(
            and_(
                Servicio.id_taller == taller_id,
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin,
                Servicio.estado == EstadoServicio.cancelado
            )
        )
        
        result_cancelados = await db.execute(query_cancelados)
        total_cancelados = result_cancelados.scalar() or 0
        
        # Cancelados por estado de solicitud (motivo)
        query_motivos = select(
            SolicitudServicio.estado,
            func.count(Servicio.id).label('cantidad')
        ).join(
            Servicio, SolicitudServicio.id == Servicio.id_solicitud_servicio
        ).where(
            and_(
                Servicio.id_taller == taller_id,
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin,
                Servicio.estado == EstadoServicio.cancelado
            )
        ).group_by(SolicitudServicio.estado)
        
        result_motivos = await db.execute(query_motivos)
        motivos = {row.estado: row.cantidad for row in result_motivos.all()}
        
        porcentaje = (total_cancelados / total_servicios * 100) if total_servicios > 0 else 0.0
        
        return CasosCanceladosKPI(
            total_cancelados=total_cancelados,
            total_servicios=total_servicios,
            porcentaje_cancelados=round(porcentaje, 2),
            cancelados_por_motivo=motivos
        )
    
    @staticmethod
    async def _calcular_cumplimiento_sla(
        db: AsyncSession,
        taller_id: int,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> SLAKPI:
        """Calcula el nivel de cumplimiento SLA"""
        
        # SLA: 30 minutos para llegar al lugar (configurable)
        sla_minutos = 30
        
        # Total de servicios finalizados
        query_total = select(func.count(Servicio.id)).where(
            and_(
                Servicio.id_taller == taller_id,
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin,
                Servicio.estado == EstadoServicio.finalizado
            )
        )
        
        result_total = await db.execute(query_total)
        total_servicios = result_total.scalar() or 0
        
        # Servicios que llegaron dentro del SLA
        # Buscamos servicios donde el tiempo hasta "en_lugar" fue <= 30 minutos
        query_sla = select(func.count(Servicio.id)).where(
            and_(
                Servicio.id_taller == taller_id,
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin,
                Servicio.estado == EstadoServicio.finalizado
            )
        )
        
        # Necesitamos calcular el tiempo hasta en_lugar para cada servicio
        query_servicios = select(Servicio).where(
            and_(
                Servicio.id_taller == taller_id,
                Servicio.fecha >= fecha_inicio,
                Servicio.fecha <= fecha_fin,
                Servicio.estado == EstadoServicio.finalizado
            )
        ).options(selectinload(Servicio.historial_estados))
        
        result_servicios = await db.execute(query_servicios)
        servicios = result_servicios.scalars().all()
        
        servicios_dentro_sla = 0
        for servicio in servicios:
            # Buscar el historial con estado "en_lugar"
            historial_en_lugar = None
            for hist in servicio.historial_estados:
                if hist.estado == EstadoServicio.en_lugar:
                    historial_en_lugar = hist
                    break
            
            if historial_en_lugar:
                tiempo_lugar = historial_en_lugar.tiempo
                if tiempo_lugar.tzinfo is not None:
                    tiempo_lugar = tiempo_lugar.replace(tzinfo=None)
                fecha_servicio = servicio.fecha
                if fecha_servicio.tzinfo is not None:
                    fecha_servicio = fecha_servicio.replace(tzinfo=None)
                tiempo_minutos = (tiempo_lugar - fecha_servicio).total_seconds() / 60
                if tiempo_minutos <= sla_minutos:
                    servicios_dentro_sla += 1
        
        porcentaje = (servicios_dentro_sla / total_servicios * 100) if total_servicios > 0 else 0.0
        
        return SLAKPI(
            total_servicios=total_servicios,
            servicios_dentro_sla=servicios_dentro_sla,
            porcentaje_cumplimiento=round(porcentaje, 2),
            sla_minutos_esperado=sla_minutos
        )
