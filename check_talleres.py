import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def check_talleres():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT id, nombre FROM taller LIMIT 5'))
        talleres = result.fetchall()
        print(f'Talleres encontrados: {len(talleres)}')
        for taller in talleres:
            print(f'  ID: {taller[0]}, Nombre: {taller[1]}')

if __name__ == "__main__":
    asyncio.run(check_talleres())
