"""
Utilidades para manejo de zona horaria
Bolivia está en UTC-4 (sin horario de verano)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# Zona horaria de Bolivia (UTC-4)
BOLIVIA_TZ = timezone(timedelta(hours=-4))


def now_bolivia() -> datetime:
    """
    Retorna la fecha/hora actual en hora de Bolivia (UTC-4)
    Como naive datetime para compatibilidad con la BD
    """
    return datetime.now(BOLIVIA_TZ).replace(tzinfo=None)


def utc_to_bolivia(dt: datetime) -> datetime:
    """
    Convierte un datetime UTC a hora de Bolivia
    
    Args:
        dt: datetime en UTC (puede ser naive o aware)
        
    Returns:
        datetime en hora Bolivia (naive)
    """
    if dt is None:
        return None
    
    # Si es naive, asumimos que es UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convertir a hora de Bolivia
    bolivia_dt = dt.astimezone(BOLIVIA_TZ)
    
    # Retornar como naive (sin timezone info) para la BD
    return bolivia_dt.replace(tzinfo=None)


def bolivia_to_utc(dt: datetime) -> datetime:
    """
    Convierte un datetime de Bolivia a UTC
    
    Args:
        dt: datetime en hora Bolivia (naive)
        
    Returns:
        datetime en UTC (naive)
    """
    if dt is None:
        return None
    
    # Asumir que el datetime naive está en hora Bolivia
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BOLIVIA_TZ)
    
    # Convertir a UTC
    utc_dt = dt.astimezone(timezone.utc)
    
    # Retornar como naive para la BD
    return utc_dt.replace(tzinfo=None)


def parse_iso_to_bolivia(iso_string: str) -> datetime:
    """
    Parsea un string ISO y lo convierte a hora de Bolivia
    
    Args:
        iso_string: String en formato ISO (ej: "2024-01-01T12:00:00Z")
        
    Returns:
        datetime en hora Bolivia (naive)
    """
    if not iso_string:
        return None
    
    # Remover 'Z' al final si existe
    if iso_string.endswith('Z'):
        iso_string = iso_string[:-1]
    
    # Parsear
    dt = datetime.fromisoformat(iso_string)
    
    # Si no tiene timezone, asumir UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convertir a Bolivia
    return utc_to_bolivia(dt)
