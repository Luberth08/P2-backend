"""
Script para limpiar referencias huérfanas en la tabla alembic_version
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings


async def fix_alembic_version():
    """Limpia referencias a migraciones que no existen."""
    
    # Crear engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True
    )
    
    # Crear sesión
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Ver qué hay en alembic_version
        print("\n=== Estado actual de alembic_version ===")
        result = await session.execute(text("SELECT * FROM alembic_version"))
        rows = result.fetchall()
        
        for row in rows:
            print(f"Versión actual: {row[0]}")
        
        # Si hay merge_heads_notifications, eliminarlo
        if any('merge_heads_notifications' in str(row) for row in rows):
            print("\n⚠️  Encontrada referencia a 'merge_heads_notifications'")
            print("🔧 Eliminando referencia huérfana...")
            
            await session.execute(text("DELETE FROM alembic_version"))
            await session.commit()
            
            print("✅ Tabla alembic_version limpiada")
            print("\nAhora ejecuta: alembic upgrade head")
        else:
            print("\n✅ No se encontró 'merge_heads_notifications'")
            print("El problema puede estar en otra parte.")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_alembic_version())
