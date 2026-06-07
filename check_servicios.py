import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def check_servicios():
    async with AsyncSessionLocal() as db:
        # Verificar servicios por taller
        result = await db.execute(text('''
            SELECT s.id_taller, t.nombre, COUNT(s.id) as total_servicios
            FROM servicio s
            JOIN taller t ON s.id_taller = t.id
            GROUP BY s.id_taller, t.nombre
        '''))
        servicios_por_taller = result.fetchall()
        
        print(f'Servicios por taller:')
        for row in servicios_por_taller:
            print(f'  Taller ID {row[0]} ({row[1]}): {row[2]} servicios')
        
        # Verificar solicitudes por taller
        result = await db.execute(text('''
            SELECT ss.id_taller, t.nombre, COUNT(ss.id) as total_solicitudes
            FROM solicitud_servicio ss
            JOIN taller t ON ss.id_taller = t.id
            GROUP BY ss.id_taller, t.nombre
        '''))
        solicitudes_por_taller = result.fetchall()
        
        print(f'\nSolicitudes por taller:')
        for row in solicitudes_por_taller:
            print(f'  Taller ID {row[0]} ({row[1]}): {row[2]} solicitudes')

if __name__ == "__main__":
    asyncio.run(check_servicios())
