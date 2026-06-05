from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# ============================================================================
# CONFIGURACIÓN DEL MOTOR DE BASE DE DATOS CON MANEJO DE CONEXIONES ROBUSTA
# ============================================================================
# Motor asincrónico para PostgreSQL con configuración optimizada para producción
# - pool_pre_ping: Verifica que la conexión esté viva antes de usarla
# - pool_size: Número de conexiones permanentes en el pool (5 por defecto)
# - max_overflow: Conexiones adicionales temporales permitidas (10 por defecto)
# - pool_recycle: Recicla conexiones cada 3600 segundos (1 hora) para evitar timeouts
# - pool_timeout: Tiempo de espera máximo para obtener una conexión (30 segundos)
# - echo: Muestra logs de SQL (útil para debug, desactivar en producción si hay muchas queries)

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # Verifica conexión antes de usar
    pool_size=5,                # Conexiones permanentes en el pool
    max_overflow=10,            # Conexiones adicionales permitidas
    pool_recycle=3600,          # Recicla conexiones cada hora
    pool_timeout=30,            # Timeout para obtener conexión
    echo=True                   # Logs de SQL (cambiar a False en producción)
)

# Fábrica de sesiones
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Dependencia para los Endpoints
async def get_db():
    """
    Genera una sesión de base de datos para cada request.
    La sesión se cierra automáticamente al terminar el request.
    
    Incluye retry automático en caso de errores de conexión.
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with AsyncSessionLocal() as session:
                yield session
                break  # Si llegamos aquí, todo funcionó correctamente
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                # Si ya agotamos los reintentos, propagar el error
                raise
            
            # Esperar un poco antes de reintentar (exponential backoff)
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            wait_time = 2 ** retry_count  # 2, 4, 8 segundos
            logger.warning(
                f"Error de conexión a la base de datos (intento {retry_count}/{max_retries}). "
                f"Reintentando en {wait_time} segundos... Error: {e}"
            )
            await asyncio.sleep(wait_time)