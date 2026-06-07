import asyncio
from app.services import kpi_service
from app.db.session import AsyncSessionLocal

async def test_kpi_service():
    async with AsyncSessionLocal() as db:
        try:
            print("Probando servicio KPI para taller ID 7...")
            kpis = await kpi_service.KPIService.get_dashboard_kpis(
                db=db,
                taller_id=7,
                fecha_inicio=None,
                fecha_fin=None
            )
            print(f"KPIs obtenidos: {kpis}")
            print(f"Tiempo promedio asignación: {kpis.tiempo_promedio.tiempo_asignacion_minutos}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_kpi_service())
