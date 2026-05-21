import logging
import sys
from app.core.config import settings

# Definir formato
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging():
    """Configura el logging para toda la aplicación."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if settings.PROJECT_NAME else logging.DEBUG)

    # Consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # Archivo (opcional, descomentar si se desea)
    # file_handler = logging.FileHandler("app.log")
    # file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    # root_logger.addHandler(file_handler)

    # Silenciar logs excesivos de librerías
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Llamar a la configuración al importar el módulo
setup_logging()

# Exportar logger por defecto
logger = logging.getLogger(__name__)