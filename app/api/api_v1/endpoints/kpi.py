from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List

from app.db.session import get_db
from app.core.deps import get_current_usuario
from app.models.usuario import Usuario
from app.services import kpi_service
from app.schemas.kpi import DashboardKPIs

router = APIRouter(tags=["KPIs - Dashboard"])


@router.get("/taller/{taller_id}/dashboard", response_model=DashboardKPIs)
async def get_taller_dashboard_kpis(
    taller_id: int,
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha de inicio del periodo (ISO 8601)"),
    fecha_fin: Optional[datetime] = Query(None, description="Fecha de fin del periodo (ISO 8601)"),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene los KPIs del dashboard para un taller específico.
    
    Por defecto, muestra los datos de los últimos 30 días si no se especifican fechas.
    """
    
    # Obtener KPIs
    try:
        kpis = await kpi_service.KPIService.get_dashboard_kpis(
            db=db,
            taller_id=taller_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        return kpis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular KPIs: {str(e)}"
        )


@router.get("/general/dashboard", response_model=List[DashboardKPIs])
async def get_general_dashboard_kpis(
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha de inicio del periodo (ISO 8601)"),
    fecha_fin: Optional[datetime] = Query(None, description="Fecha de fin del periodo (ISO 8601)"),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene los KPIs del dashboard para todos los talleres (vista general del administrador).
    
    Por defecto, muestra los datos de los últimos 30 días si no se especifican fechas.
    """
    
    try:
        # Obtener todos los talleres
        from sqlalchemy import select, text
        result = await db.execute(text("SELECT id FROM taller"))
        taller_ids = [row[0] for row in result.fetchall()]
        
        print(f"Talleres encontrados: {taller_ids}")
        
        if not taller_ids:
            return []
        
        # Obtener KPIs para cada taller
        kpis_list = []
        for taller_id in taller_ids:
            try:
                print(f"Obteniendo KPIs para taller {taller_id}")
                kpis = await kpi_service.KPIService.get_dashboard_kpis(
                    db=db,
                    taller_id=taller_id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )
                kpis_list.append(kpis)
                print(f"KPIs obtenidos para taller {taller_id}")
            except Exception as e:
                # Si falla un taller, continuar con los demás
                print(f"Error al obtener KPIs para taller {taller_id}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"Total KPIs obtenidos: {len(kpis_list)}")
        return kpis_list
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular KPIs generales: {str(e)}"
        )
