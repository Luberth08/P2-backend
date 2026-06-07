from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class TiempoPromedioKPI(BaseModel):
    """KPI de tiempos promedio"""
    tiempo_asignacion_minutos: float  # Tiempo entre reporte y taller asignado
    tiempo_llegada_minutos: float  # Tiempo entre asignación y llegada
    
    class Config:
        from_attributes = True


class IncidentePorTipoKPI(BaseModel):
    """KPI de incidentes por tipo"""
    tipo: str
    cantidad: int
    porcentaje: float
    
    class Config:
        from_attributes = True


class TallerEficienteKPI(BaseModel):
    """KPI de talleres más eficientes"""
    taller_id: int
    nombre: str
    tiempo_respuesta_promedio_minutos: float
    tiempo_finalizacion_promedio_minutos: float
    total_servicios: int
    
    class Config:
        from_attributes = True


class ZonaIncidenteKPI(BaseModel):
    """KPI de zonas con más incidentes"""
    zona: str
    latitud_promedio: float
    longitud_promedio: float
    cantidad_incidentes: int
    
    class Config:
        from_attributes = True


class CasosCanceladosKPI(BaseModel):
    """KPI de casos cancelados"""
    total_cancelados: int
    total_servicios: int
    porcentaje_cancelados: float
    cancelados_por_motivo: Dict[str, int]
    
    class Config:
        from_attributes = True


class SLAKPI(BaseModel):
    """KPI de nivel de cumplimiento SLA"""
    total_servicios: int
    servicios_dentro_sla: int
    porcentaje_cumplimiento: float
    sla_minutos_esperado: int
    
    class Config:
        from_attributes = True


class DashboardKPIs(BaseModel):
    """Dashboard completo de KPIs para un taller"""
    taller_id: int
    nombre: str  # Nombre del taller
    periodo_inicio: datetime
    periodo_fin: datetime
    
    # KPIs principales
    tiempo_promedio: TiempoPromedioKPI
    incidentes_por_tipo: List[IncidentePorTipoKPI]
    talleres_eficientes: List[TallerEficienteKPI]
    zonas_incidentes: List[ZonaIncidenteKPI]
    casos_cancelados: CasosCanceladosKPI
    cumplimiento_sla: SLAKPI
    
    class Config:
        from_attributes = True
