from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

#Motor asincronico para PostgreSQL
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=True)

#Fabrica de sesiones
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Dependencia para los Endpoints
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session