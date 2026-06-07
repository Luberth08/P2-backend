import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.begin() as conn:
        # Verificar si los tipos enum existen
        result = await conn.execute(text("""
            SELECT typname FROM pg_type WHERE typname LIKE 'estadoquote%'
        """))
        print('Tipos enum de cotización:', [row[0] for row in result])
        
        # Verificar el tipo de las columnas estado
        result2 = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name IN ('quote_request', 'quote_response') 
            AND column_name = 'estado'
        """))
        print('Tipos de columnas estado:', [(row[0], row[1]) for row in result2])

asyncio.run(check())
